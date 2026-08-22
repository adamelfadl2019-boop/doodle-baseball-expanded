from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import http.server
import json
import platform
import re
import shutil
import socketserver
import sys
import threading
import traceback
import webbrowser
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PAYLOAD = PACKAGE_DIR / "payload"
VERSION = "V19"
BUILD_NAME = "GitHub Release Edition"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def looks_like_repo(root: Path) -> bool:
    return (
        (root / "doodle-baseball" / "js" / "game.js").is_file()
        and (root / "doodle-baseball" / "assets").is_dir()
        and (root / "doodle-baseball.html").is_file()
    )


def find_repo() -> Path | None:
    candidates = []
    for start in [PACKAGE_DIR, Path.cwd()]:
        for p in [start, *start.parents]:
            if looks_like_repo(p):
                candidates.append(p)

    for base in [Path.home() / "Downloads", Path.home() / "Desktop"]:
        if not base.exists():
            continue
        try:
            for game in base.glob("**/doodle-baseball/js/game.js"):
                root = game.parents[2]
                if looks_like_repo(root):
                    candidates.append(root)
        except (PermissionError, OSError):
            pass

    seen, unique = set(), []
    for c in candidates:
        try:
            key = str(c.resolve()).lower()
        except OSError:
            key = str(c).lower()
        if key not in seen:
            seen.add(key)
            unique.append(c)

    if not unique:
        return None

    def score(p: Path):
        try:
            return (p / "doodle-baseball" / "js" / "game.js").stat().st_mtime
        except OSError:
            return 0

    return max(unique, key=score)


def patch_game(source: str):
    text = source
    applied, missing = [], []

    def sub(name, pattern, replacement, flags=0):
        nonlocal text
        new, count = re.subn(pattern, replacement, text, count=1, flags=flags)
        if count == 1:
            text = new
            applied.append(name)
        else:
            missing.append(name)

    sub(
        "speed multiplier",
        r"var h = g \* d\.V,",
        "var h = g * d.V * (null == window.DBE_SPEED_MULT ? 1 : window.DBE_SPEED_MULT),",
    )

    sub(
        "per-pitch contact rule",
        r"var c = \(H\(b\)\.g - H\(a\.i\)\.g\) / 3;\s*if \(1 >= Math\.abs\(c\) && 1 == b\.o\) \{",
        """var c = (H(b).g - H(a.i).g) / 3;
            var __dbeRule = window.DBE_CONTACT_RULE ? window.DBE_CONTACT_RULE(b.$) : null,
              __dbeCenter = __dbeRule && "number" == typeof __dbeRule.center ? __dbeRule.center : 0,
              __dbeBaseWindow = __dbeRule && "number" == typeof __dbeRule.window ? __dbeRule.window : 1,
              __dbePitchWindow = __dbeBaseWindow * (window.DBE_HIT_WINDOW || 1),
              __dbeContactError = c - __dbeCenter;
            if (__dbePitchWindow >= Math.abs(__dbeContactError) && 1 == b.o) {""",
        re.MULTILINE,
    )
    sub(
        "per-pitch inner contact bound",
        r"if \(!\(-1 > c \|\| 1 < c\)\) \{",
        "if (!(-__dbePitchWindow > __dbeContactError || __dbePitchWindow < __dbeContactError)) {",
    )

    sub("force home run toggle", r"var c = 92 < b;", "var c = !!window.DBE_FORCE_HR || 92 < b;")
    sub(
        "run multiplier",
        r"a\.\$ \? x\(w\.ka\(\), 4, a\.\$\) : a\.ta && x\(w\.ka\(\), 23, a\.ta\);",
        "a.$ ? x(w.ka(), 4, a.$ * (window.DBE_SCORE_MULT || 1)) : a.ta && x(w.ka(), 23, a.ta);",
    )
    sub(
        "difficulty ramp toggle",
        r"this\.V = Math\.min\(this\.V \+ 0\.01 \* b, 2\);",
        "window.DBE_NO_RAMP || (this.V = Math.min(this.V + 0.01 * b, 2));",
    )

    # The stock game uses uh (normally 3, hidden mode=1 uses 10).
    # V6 reads a live mod-controlled out limit instead.
    sub(
        "adjustable out limit",
        r"if \(a\.ya >= uh\) \{",
        "if (a.ya >= (window.DBE_OUT_LIMIT || uh)) {",
    )

    sub(
        "event bridge",
        r"zm\.prototype\.Za = function \(a, b\) \{",
        'zm.prototype.Za = function (a, b) {\n    try { window.dispatchEvent(new CustomEvent("dbe-game-event", { detail: { type: a, value: b } })); } catch (__dbeEventError) {}',
    )
    sub(
        "game instance bridge",
        r"a && b && \(\(Em = new zm\(a, b, d\)\), Em\.start\(\)\);",
        "a && b && ((Em = new zm(a, b, d)), (window.DBE_GAME = Em), Em.start());",
    )

    # Queue exact pitch before windup, use a vanilla animation as the animation shell,
    # but keep the custom pitch ID for physics/contact.
    sub(
        "queued pitch selector and animation base",
        r"jj\.prototype\.pitch = function \(\) \{\s*var a = this,\s*b = this\.V\[Math\.floor\(Math\.random\(\) \* this\.V\.length\)\],\s*c = lj\.get\(b\);",
        """jj.prototype.pitch = function () {
    var a = this,
      b = null != this.__dbeLockedPitch
        ? this.__dbeLockedPitch
        : (null != this.__dbeQueuedPitch ? this.__dbeQueuedPitch : this.V[Math.floor(Math.random() * this.V.length)]);
    this.__dbeQueuedPitch = null;
    b = window.DBE_PICK_PITCH && null == this.__dbeWasQueued && null == this.__dbeLockedPitch
      ? window.DBE_PICK_PITCH(this.Ga, b, this.V)
      : b;
    this.__dbeWasQueued = null;
    var __dbeAnimPitch = window.DBE_PITCH_ANIM_BASE ? window.DBE_PITCH_ANIM_BASE(b) : b,
      c = lj.get(__dbeAnimPitch);""",
        re.MULTILINE,
    )

    # Mark the real separate pitcher-hat sprite with the custom pitch color.
    sub(
        "real pitcher hat tint marker",
        r"this\.Ea = this\.i\.Fa = 1;",
        """this.Ea = this.i.Fa = 1;
    this.Ca.__dbeIsPitcherHat = true;
    this.Ca.__dbeHatColor = window.DBE_PITCH_HAT_COLOR ? window.DBE_PITCH_HAT_COLOR(b) : null;""",
    )

    # V is the actual sprite renderer used by the pitcher's separate cap object.
    # Tint only objects carrying __dbeHatColor, using an offscreen copy supplied by the mod.
    sub(
        "real sprite hat tint renderer",
        r"V\.prototype\.Wb = function \(a, b, c, d, e, f\) \{\s*qf\(this\.Ba\(\), this\.ta, a, b, c, d, e, f, this\.ac \|\| this\.\$b\);\s*\};",
        """V.prototype.Wb = function (a, b, c, d, e, f) {
    var __dbeHatColor = this.__dbeIsPitcherHat && window.DBE_DISPLAY_PITCH_COLOR
      ? window.DBE_DISPLAY_PITCH_COLOR
      : this.__dbeHatColor;
    if (__dbeHatColor && window.DBE_TINT_SPRITE) {
      var __dbeScale = this.ac || this.$b || 1,
        __dbeSource = nf(this.Ba(), this.ta, __dbeScale);
      if (__dbeSource) {
        var __dbeTinted = window.DBE_TINT_SPRITE(__dbeSource, __dbeHatColor),
          __dbePad = (10 * d) / this.ta[3];
        f && a.scale(-1, 1);
        a.drawImage(__dbeTinted, b - (d + __dbePad) / 2, c - (e + __dbePad) / 2, d + __dbePad, e + __dbePad);
        f && a.scale(-1, 1);
        return;
      }
    }
    qf(this.Ba(), this.ta, a, b, c, d, e, f, this.ac || this.$b);
  };""",
        re.MULTILINE,
    )

    sub(
        "first pitch early queue",
        r"wi\(\);\s*J\(a\.Fa, 1700, function \(\) \{",
        """wi();
      try { window.DBE_PREPARE_PITCH && window.DBE_PREPARE_PITCH(a.T.U); } catch (__dbePrepFirstError) {}
      J(a.Fa, 1700, function () {""",
        re.MULTILINE,
    )
    sub(
        "between pitch early queue",
        r"Sj\(a\);\s*J\(a\.v, 1500, function \(\) \{",
        """Sj(a);
      try { window.DBE_PREPARE_PITCH && window.DBE_PREPARE_PITCH(a.U); } catch (__dbePrepNextError) {}
      J(a.v, 1500, function () {""",
        re.MULTILINE,
    )
    sub(
        "pitch release event",
        r"a\.i\.Fa = 0;\s*T\(a, c\.Da\);\s*a\.Ea = 2;\s*a\.i\.pitch\(b\);",
        'a.i.Fa = 0;\n      T(a, c.Da);\n      a.Ea = 2;\n      a.i.pitch(b);\n      try { window.dispatchEvent(new CustomEvent("dbe-pitch-release", { detail: { id: (window.DBE_ACTIVE_PROFILE_ID || 0), variantId: (window.DBE_ACTIVE_VARIANT_ID || 1), challengeId: (window.DBE_ACTIVE_CHALLENGE_ID || 0), engineId: b, count: a.Ga + 1 } })); } catch (__dbePitchEventError) {}\n      try { window.DBE_RELEASE_PITCH_LOCK && window.DBE_RELEASE_PITCH_LOCK(a, b); } catch (__dbeReleaseLockError) {}',
        re.MULTILINE,
    )
    sub("custom pitch sound mapping", r"mj\.get\(b\)\.play\(\);", "mj.get(__dbeAnimPitch).play();")

    sub(
        "custom base pitch speed",
        r"Ih\(this, rd\(b\)\.scale\(Kh\[a\]\)\);",
        "var __dbeBaseSpeed = window.DBE_PITCH_BASE_SPEED ? Number(window.DBE_PITCH_BASE_SPEED(a, Kh[a])) : Kh[a],\n      __dbeSpeedMult = window.DBE_PITCH_SPEED_MULT ? Number(window.DBE_PITCH_SPEED_MULT(a)) : 1;\n    isFinite(__dbeBaseSpeed) && 0 < __dbeBaseSpeed || (__dbeBaseSpeed = Kh[a] || 30);\n    isFinite(__dbeSpeedMult) && 0 < __dbeSpeedMult || (__dbeSpeedMult = 1);\n    Ih(this, rd(b).scale(__dbeBaseSpeed * __dbeSpeedMult));",
    )
    sub(
        "separate profile motion layer",
        r"case 5:\s*this\.S = Math\.max\(0, 1 - 1\.4 \* b\);\s*\}",
        """case 5:
            this.S = Math.max(0, 1 - 1.4 * b);
        }
        try {
          var __dbeOffset = window.DBE_PROFILE_OFFSET ? window.DBE_PROFILE_OFFSET(b) : null;
          if (__dbeOffset && isFinite(__dbeOffset.x) && isFinite(__dbeOffset.y))
            this.j(c.x + __dbeOffset.x, c.y + __dbeOffset.y, d.g);
        } catch (__dbeProfileMotionError) {}""",
        re.MULTILINE,
    )

    sub(
        "physical outfield wall stable phase",
        r"Fh\.prototype\.Aa = function \(a\) \{\s*Jg\.prototype\.Aa\.call\(this, a\);",
        """Fh.prototype.Aa = function (a) {
    Jg.prototype.Aa.call(this, a);
    try {
      if (2 == this.o) {
        var __dbeGroundPos = H(this);
        if (__dbeGroundPos && __dbeGroundPos.y <= 0.18) this.__dbeGroundTouched = !0;
      }
    } catch (__dbeGroundTouchError) {}
    try {
      this.__dbeWallCooldown = Math.max(0, (this.__dbeWallCooldown || 0) - a);
      if (window.DBE_WALL_PHYSICS !== false && 2 == this.o && !this.__dbeWallCooldown) {
        var __dbePos = H(this), __dbeDx = __dbePos.x - A.x, __dbeDz = __dbePos.g - A.g,
          __dbeR = Math.sqrt(__dbeDx * __dbeDx + __dbeDz * __dbeDz);
        if (__dbeR > 89.35 && __dbePos.y < (window.DBE_WALL_HEIGHT || 2.2)) {
          var __dbeNx = __dbeDx / Math.max(0.001, __dbeR), __dbeNz = __dbeDz / Math.max(0.001, __dbeR),
            __dbeVx = this.i.i.x, __dbeVz = this.i.i.g, __dbeDot = __dbeVx * __dbeNx + __dbeVz * __dbeNz;
          if (0 < __dbeDot) {
            this.i.i.x = (__dbeVx - 1.70 * __dbeDot * __dbeNx) * 0.66;
            this.i.i.g = (__dbeVz - 1.70 * __dbeDot * __dbeNz) * 0.66;
            this.i.i.y *= 0.78;
            this.j(A.x + __dbeNx * 89.05, Math.max(0.08, __dbePos.y), A.g + __dbeNz * 89.05);
            this.__dbeWallCooldown = 260;
            try { window.dispatchEvent(new CustomEvent("dbe-wall-bounce")); } catch (__dbeWallEventError) {}
          }
        }
      }
    } catch (__dbeWallPhysicsError) {}""",
        re.MULTILINE,
    )

    sub(
        "expanded custom pitch trails",
        r"return 2 == a\.o \|\| \(1 == a\.o && \(1 == a\.\$ \|\| 2 == a\.\$ \|\| 3 == a\.\$\)\);",
        "return 2 == a.o || (1 == a.o && (1 == a.$ || 2 == a.$ || 3 == a.$ || (window.DBE_PROFILE_TRAIL && window.DBE_PROFILE_TRAIL())));",
    )

    sub(
        "real fielder array bridge",
        r"this\.i = \[\];\s*for \(var c = n\(uj\), d = c\.next\(\); !d\.done; d = c\.next\(\)\)",
        """this.i = [];
    try { window.DBE_FIELDERS = this.i; } catch (__dbeFielderArrayBridgeError) {}
    for (var c = n(uj), d = c.next(); !d.done; d = c.next())""",
        re.MULTILINE,
    )

    # V19 SAFE DEFENSE:
    # Do not suppress Nj() and do not replace the batter lifecycle.
    # Pickups only record a result. The result is consumed at the original runner callback.
    sub(
        "real fielder pickup bridge",
        r"rj = function \(a\) \{\s*Gh\(a\.i, 0\);\s*x\(Eh, 9\);\s*pj\(a, 2\);",
        """rj = function (a) {
    Gh(a.i, 0);
    x(Eh, 9);
    pj(a, 2);
    try {
      var __dbeBallPos = H(a.i), __dbeFielderPos = H(a);
      window.DBE_FIELDER_PICKUP && window.DBE_FIELDER_PICKUP({
        ground: !!a.i.__dbeGroundTouched,
        ballX: __dbeBallPos.x, ballY: __dbeBallPos.y, ballZ: __dbeBallPos.g,
        fielderX: __dbeFielderPos.x, fielderY: __dbeFielderPos.y, fielderZ: __dbeFielderPos.g,
        arm: a.U && a.U.nb ? "strong" : "normal"
      });
    } catch (__dbePickupBridgeError) {}""",
        re.MULTILINE,
    )

    # Ground balls visually throw toward first base instead of always returning to the pitcher.
    sub(
        "visual throw to first",
        r"sj = function \(a\) \{\s*var b = a\.i,\s*c = H\(a\.V\);",
        """sj = function (a) {
    var b = a.i,
      c = window.DBE_THROW_FIRST
        ? (window.DBE_FIELDERS && window.DBE_FIELDERS[3] ? qj(window.DBE_FIELDERS[3]) : zd[0])
        : H(a.V);""",
        re.MULTILINE,
    )

    # Foul is handled before Si() starts, so the hitter never runs the bases.
    # Defensive outs are handled at Si()'s NORMAL completion callback.
    __dbeNjPattern = re.compile(
        r"""Si\(a\.i,\s*b,\s*function\s*\(e\)\s*\{\s*
            a\.ta\+\+;\s*
            e\s*\|\|\s*\(!b\s*&&\s*2\s*!=\s*a\.o\.o\)\s*
            \?\s*\(e\s*\?\s*Pj\(a,\s*a\.i\)\s*:\s*a\.V\.push\(a\.i\),\s*\(a\.i\s*=\s*null\),\s*Qj\(a\)\)\s*
            :\s*Nj\(a,\s*b\);\s*
        \}\);""",
        re.MULTILINE | re.DOTALL | re.VERBOSE,
    )
    __dbeNjReplacement = r"""if (window.DBE_FOUL_PENDING && window.DBE_SAFE_FOUL && window.DBE_SAFE_FOUL()) {
      var __dbeFoulConfig = a.i && a.i.v;
      try { a.i && jg(a.i); } catch (__dbeFoulDisposeError) {}
      a.i = null;
      a.ta = 0;
      a.$ = 0;
      try {
        if (__dbeFoulConfig) {
          a.i = new Bi(__dbeFoulConfig);
          a.i.j(Ad.j());
          E(a.i, a.ha);
          Ii(a.i, 8);
        }
      } catch (__dbeFoulBatterResetError) {}
      Qj(a);
      return;
    }
    Si(a.i, b, function (e) {
      a.ta++;
      var __dbeDefenseResult = null;
      try {
        __dbeDefenseResult = window.DBE_SAFE_DEFENSE_RESULT ? window.DBE_SAFE_DEFENSE_RESULT() : null;
      } catch (__dbeDefenseResultError) {}
      if (__dbeDefenseResult && __dbeDefenseResult.out) {
        try { a.i && jg(a.i); } catch (__dbeDefenseDisposeError) {}
        a.i = null;
        a.ta = 0;
        a.$ = 0;
        a.ya++;
        x(w.ka(), 2, a.ya);
        qi(a.ya);
        try {
          window.dispatchEvent(new CustomEvent("dbe-defense-native-out", {
            detail: {
              reason: __dbeDefenseResult.reason || "DEFENSIVE OUT",
              margin: Number(__dbeDefenseResult.margin) || 0,
              outs: a.ya
            }
          }));
        } catch (__dbeDefenseOutEventError) {}
        if (a.ya >= (window.DBE_OUT_LIMIT || uh)) {
          a.W = 5;
          try {
            window.dispatchEvent(new CustomEvent("dbe-defense-game-over", {
              detail: { outs: a.ya }
            }));
          } catch (__dbeDefenseGameOverEventError) {}
        } else {
          Qj(a);
        }
        return;
      }
      if (__dbeDefenseResult && __dbeDefenseResult.safe) {
        try {
          window.dispatchEvent(new CustomEvent("dbe-defense-safe", {
            detail: {
              reason: __dbeDefenseResult.reason || "SAFE",
              margin: Number(__dbeDefenseResult.margin) || 0
            }
          }));
        } catch (__dbeDefenseSafeEventError) {}
      }
      e || (!b && 2 != a.o.o)
        ? (e ? Pj(a, a.i) : a.V.push(a.i), (a.i = null), Qj(a))
        : Nj(a, b);
    });"""
    __dbeNjNew, __dbeNjCount = __dbeNjPattern.subn(__dbeNjReplacement, text, count=1)
    if __dbeNjCount == 1:
        text = __dbeNjNew
        applied.append("safe natural-lifecycle defense resolution")
    else:
        # Defense remains disabled rather than applying a partial lifecycle patch.
        applied.append("safe defense resolution (compat fallback disabled)")

    sub(
        "contact quality bridge",
        r"b\.Pa = 30;",
        'b.Pa = 30;\n                try { window.DBE_ON_CONTACT && window.DBE_ON_CONTACT(b.$, __dbeContactError, __dbePitchWindow, a.i); } catch (__dbeContactBridgeError) {}',
    )

    sub(
        "custom contact power",
        r"Math\.max\(0\.2, 1 - Math\.abs\(c\)\) \* Nh\[b\.\$\]",
        "Math.max(0.2, 1 - Math.min(1, Math.abs(__dbeContactError) / Math.max(0.001, __dbePitchWindow))) * ((window.DBE_PITCH_HIT_POWER && window.DBE_PITCH_HIT_POWER(b.$)) || Nh[b.$] || 1.3)",
    )

    sub(
        "bat power variation",
        r"d = -1\.3 \* b\.i\.i\.g \* d \+ \(Math\.abs\(b\.i\.i\.g\) / 2\) \* \(1 - d\);",
        "d = -1.3 * b.i.i.g * d + (Math.abs(b.i.i.g) / 2) * (1 - d);\n                d *= window.DBE_BAT_POWER_MULT ? window.DBE_BAT_POWER_MULT(b.$, __dbeContactError, __dbePitchWindow, a.i) : 1;",
    )

    sub(
        "bat spray and elevation physics",
        r"Mh\(d, 40 < d \? 60 : 110, 90 \+ \(c / Math\.abs\(c\)\) \* 5 \+ 40 \* c\)",
        "Mh(d, window.DBE_BAT_ELEVATION ? window.DBE_BAT_ELEVATION(d, __dbeContactError, __dbePitchWindow) : (40 < d ? 60 : 110), window.DBE_BAT_SPRAY_ANGLE ? window.DBE_BAT_SPRAY_ANGLE(__dbeContactError, __dbePitchWindow) : (90 + 40 * c))",
    )

    # Optional runner-speed phase. If source formatting differs, keep vanilla speed.
    __dbeRunPattern = re.compile(
        r"(Ki = function \(a, b\) \{.*?new P\(a, )28e3 / 26\.8(, zd\[a\.U - 1\].*?J\(a\.o, )28e3 / 26\.8(\);\s*\},)",
        re.MULTILINE | re.DOTALL,
    )
    __dbeRunReplacement = (
        r"\1(window.DBE_RUN_DURATION ? window.DBE_RUN_DURATION(a) : 28e3 / 26.8)"
        r"\2(window.DBE_RUN_DURATION ? window.DBE_RUN_DURATION(a) : 28e3 / 26.8)\3"
    )
    __dbeRunNew, __dbeRunCount = __dbeRunPattern.subn(__dbeRunReplacement, text, count=1)
    if __dbeRunCount == 1:
        text = __dbeRunNew
        applied.append("character runner speed stable phase")

    sub(
        "full character config encyclopedia bridge",
        r"var Xh = function \(\) \{",
        """var Xh = function () {
    try { window.DBE_CHARACTER_CONFIGS = Vh; } catch (__dbeCharacterConfigBridgeError) {}""",
        re.MULTILINE,
    )

    sub(
        "pitch seam colors",
        r'a\.strokeStyle = "red"; // TODO: loading ball stripe color',
        'a.strokeStyle = window.DBE_PITCH_COLOR ? window.DBE_PITCH_COLOR() : "red"; // V13 profile color',
    )

    if missing:
        raise RuntimeError("Unexpected Baseball game.js build. Missing: " + ", ".join(missing))
    return text, applied

def replace_function(text: str, name: str, replacement: str) -> str:
    start = text.find(f"function {name}(")
    if start < 0:
        raise RuntimeError(f"Could not find {name}()")
    brace = text.find("{", start)
    depth = 0
    quote = None
    escape = False
    i = brace
    while i < len(text):
        ch = text[i]
        if quote:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"', "`"):
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[:start] + replacement + text[i + 1:]
        i += 1
    raise RuntimeError(f"Could not parse {name}()")


def build_clean_launcher(original: str) -> str:
    text = original

    # Remove standalone external ad/analytics tags.
    for host in [
        "pagead2.googlesyndication.com",
        "stats.senty.com.au",
        "googletagmanager.com",
    ]:
        text = re.sub(
            rf'<script\b[^>]*src=["\'][^"\']*{re.escape(host)}[^"\']*["\'][^>]*>\s*</script>',
            "",
            text,
            flags=re.I | re.S,
        )

    clean_load = '''function loadJuice() {
        const splash = document.querySelector("#splash");
        if (splash) splash.remove();

        if (!document.querySelector("script[data-dbe-mod]")) {
          const mod = document.createElement("script");
          mod.src = "/doodle-baseball/mods/dbe-mod.js";
          mod.dataset.dbeMod = "1";
          document.body.appendChild(mod);
        }

        if (!document.querySelector("script[data-dbe-game]")) {
          const game = document.createElement("script");
          game.src = "/doodle-baseball/js/game-modded.js";
          game.dataset.dbeGame = "1";
          document.body.appendChild(game);
        }
      }'''
    text = replace_function(text, "loadJuice", clean_load)

    # checkRestart() from the site used to call an ad helper.
    text = text.replace("          showAd();\n", "")

    extra_style = '''
    <style id="dbe-clean-style">
      /* Preserve original game dimensions during startup. */
      .ad-top,.ad-bottom,.ad-left,.ad-right,.sticky-sidebar-video,
      .cricket-games,.game-link,body>h1{display:none!important}
      html,body{margin:0!important;background:#000!important}
      #hpcanvas{outline:none!important}
      #splash{z-index:999999!important}
    </style>
    '''
    text = text.replace("</head>", extra_style + "\n</head>", 1)
    return text


def install(repo: Path):
    game_path = repo / "doodle-baseball" / "js" / "game.js"
    original_html_path = repo / "doodle-baseball.html"

    source = game_path.read_text(encoding="utf-8")
    original_html = original_html_path.read_text(encoding="utf-8")

    if 'const assetsPath = "/doodle-baseball/assets/";' not in source:
        raise RuntimeError("Found the wrong game.js.")

    source_sha = sha256_text(source)
    modded, applied = patch_game(source)

    mods_dir = repo / "doodle-baseball" / "mods"
    mods_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PAYLOAD / "dbe-mod.js", mods_dir / "dbe-mod.js")
    (repo / "doodle-baseball" / "js" / "game-modded.js").write_text(modded, encoding="utf-8")
    clean_html = build_clean_launcher(original_html)
    (repo / "doodle-baseball-modded.html").write_text(clean_html, encoding="utf-8")

    # Normal offline/local copy. This still relies on the user's own original assets.
    offline_js = modded.replace(
        'const assetsPath = "/doodle-baseball/assets/";',
        'const assetsPath = "./doodle-baseball/assets/";',
        1,
    )
    (repo / "doodle-baseball" / "js" / "game-modded-offline.js").write_text(
        offline_js, encoding="utf-8"
    )
    offline_html = clean_html.replace(
        '"/doodle-baseball/', '"./doodle-baseball/'
    ).replace(
        "'/doodle-baseball/", "'./doodle-baseball/"
    ).replace(
        './doodle-baseball/js/game-modded.js',
        './doodle-baseball/js/game-modded-offline.js'
    )
    (repo / "doodle-baseball-offline.html").write_text(offline_html, encoding="utf-8")

    # Machine-readable diagnostics for the in-game F9 console / GitHub issue reports.
    report = {
        "version": VERSION,
        "buildName": BUILD_NAME,
        "generatedAtUtc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "sourceSha256": source_sha,
        "sourceBytes": len(source.encode("utf-8")),
        "patchCount": len(applied),
        "patches": applied,
        "repoFolderName": repo.name,
        "python": platform.python_version(),
        "platform": platform.system(),
        "architecture": platform.machine(),
        "files": {
            "modScript": "doodle-baseball/mods/dbe-mod.js",
            "gameScript": "doodle-baseball/js/game-modded.js",
            "launcher": "doodle-baseball-modded.html",
            "offlineLauncher": "doodle-baseball-offline.html",
        },
    }
    write_json(mods_dir / "dbe-build-report.json", report)
    return applied, report


def diagnose(repo: Path):
    game_path = repo / "doodle-baseball" / "js" / "game.js"
    original_html_path = repo / "doodle-baseball.html"
    if not looks_like_repo(repo):
        raise RuntimeError("That folder does not look like the expected Doodle Baseball repo.")
    source = game_path.read_text(encoding="utf-8")
    original_html = original_html_path.read_text(encoding="utf-8")
    modded, applied = patch_game(source)
    build_clean_launcher(original_html)
    return {
        "version": VERSION,
        "buildName": BUILD_NAME,
        "sourceSha256": sha256_text(source),
        "sourceBytes": len(source.encode("utf-8")),
        "patchCount": len(applied),
        "patches": applied,
        "moddedBytes": len(modded.encode("utf-8")),
        "repoFolderName": repo.name,
        "status": "PASS",
    }


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass


def serve(repo: Path, open_browser: bool = True, requested_port: int = 0):
    handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(repo), **kwargs)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", requested_port), handler) as httpd:
        port = httpd.server_address[1]
        url = f"http://127.0.0.1:{port}/doodle-baseball-modded.html"
        print("\nREAL Doodle Baseball Mod V19 is running.")
        print("Original files are untouched.")
        print("Close this window when you're done.\n")
        print(url)
        if open_browser:
            threading.Timer(0.7, lambda: webbrowser.open(url)).start()
        httpd.serve_forever()


def main():
    parser = argparse.ArgumentParser(
        description="Doodle Baseball Expanded V19 installer / diagnostics"
    )
    parser.add_argument("--repo", type=Path, help="Explicit path to doodlecricket.github.io repo")
    parser.add_argument("--diagnose", action="store_true", help="Dry-run all patch checks without writing files")
    parser.add_argument("--no-browser", action="store_true", help="Start the local server without opening a browser")
    parser.add_argument("--port", type=int, default=0, help="Local server port (0 = automatic)")
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    args = parser.parse_args()

    if args.version:
        print(f"Doodle Baseball Expanded {VERSION} — {BUILD_NAME}")
        return

    print(f"Doodle Baseball Expanded {VERSION} — {BUILD_NAME}")
    print("Finding your existing Doodle Baseball files...")
    repo = args.repo.expanduser().resolve() if args.repo else find_repo()
    if not repo:
        print("\nCould not find the repo automatically.")
        print("Put this mod folder inside your doodlecricket.github.io-master folder, or use --repo PATH.")
        if sys.stdin.isatty():
            input("\nPress Enter to close...")
        return

    print("Found:", repo)
    try:
        if args.diagnose:
            report = diagnose(repo)
            print("\nDIAGNOSTICS PASS")
            print("Source SHA-256:", report["sourceSha256"])
            print("Verified patches:", report["patchCount"])
            for item in report["patches"]:
                print("  ✓", item)
            return

        applied, report = install(repo)
    except Exception as e:
        error_path = PACKAGE_DIR / "DBE_LAST_ERROR.txt"
        error_path.write_text(
            f"Doodle Baseball Expanded {VERSION} — build failure\n\n"
            f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}",
            encoding="utf-8",
        )
        print("\nMOD BUILD FAILED:", e)
        print("Debug details written to:", error_path)
        if sys.stdin.isatty():
            input("\nPress Enter to close...")
        return

    print(f"Built {VERSION} with {len(applied)} verified patches.")
    print("Build report:", repo / "doodle-baseball" / "mods" / "dbe-build-report.json")
    serve(repo, open_browser=not args.no_browser, requested_port=args.port)


if __name__ == "__main__":
    main()
