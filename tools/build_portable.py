"""Build the fork's JVM + Android MPP using pinned public tool releases.

Requires Python 3.10+ and Java 21+. No GitHub Packages credentials are needed.
The original extension and utility classes are retained from upstream's GPL
bundle. All patch classes and Android DEX are rebuilt from this source tree.
"""
import argparse
import hashlib
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {
    "morphe-desktop-2.2.0-all.jar": (
        "https://github.com/MorpheApp/morphe-desktop/releases/download/v2.2.0/morphe-desktop-2.2.0-all.jar",
        "5ca0320ee05481df1ae3afd2f003bba3ff994d11d1f66ae48811ced71355e4fe"),
    "kotlin-compiler.zip": (
        "https://github.com/JetBrains/kotlin/releases/download/v2.4.21/kotlin-compiler-2.4.21.zip",
        "7cc140e76daf416a0424a5557f99afd7ca89ebd463ea1101261e3e01c33e75cd"),
    "r8-stable.jar": (
        "https://dl.google.com/dl/android/maven2/com/android/tools/r8/9.5.33/r8-9.5.33.jar",
        "9743e95de295fb6f5490e21da26536e4d0921809511423122ff20328a572e7f5"),
    "patches-1.3.1.mpp": (
        "https://github.com/LaKakaReal/LaKakaShitPatches/releases/download/v1.3.1/patches-1.3.1.mpp",
        "bb42a89346544c2f1a289a6695f682c52d8698c62464b493fa76c718cdc0fb45"),
}

def run(*args):
    subprocess.run([str(a) for a in args], cwd=ROOT, check=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java", default=shutil.which("java") or "java")
    parser.add_argument("--jdk", type=Path,
                        help="Optional JDK home for D8's Java library definitions")
    parser.add_argument("--tool-dir", type=Path, default=ROOT / "build/portable-tools")
    args = parser.parse_args()
    tools = args.tool_dir.resolve()
    tools.mkdir(parents=True, exist_ok=True)
    for name, (url, expected) in TOOLS.items():
        path = tools / name
        if not path.exists():
            print(f"Downloading {name}", flush=True)
            with urllib.request.urlopen(url, timeout=120) as src, path.open("wb") as dest:
                shutil.copyfileobj(src, dest)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"SHA-256 mismatch for {name}")
    kotlin = tools / "kotlin/kotlinc"
    if not (kotlin / "lib/kotlin-compiler.jar").exists():
        with zipfile.ZipFile(tools / "kotlin-compiler.zip") as archive:
            archive.extractall(tools / "kotlin")
    runtime = tools / "morphe-desktop-2.2.0-all.jar"
    version = next(line.split("=", 1)[1].strip()
                   for line in (ROOT / "gradle.properties").read_text().splitlines()
                   if line.strip().startswith("version ="))
    classes = ROOT / "build/portable-classes"
    dex = ROOT / "build/portable-dex"
    # Clear only individual generated files under these fixed build directories.
    for directory in (classes, dex):
        directory.mkdir(parents=True, exist_ok=True)
        for file in directory.rglob("*"):
            if file.is_file():
                file.unlink()
    sources = sorted((ROOT / "patches/src/main/kotlin/app/template/patches").rglob("*.kt"))
    run(args.java, "-cp", str(kotlin / "lib/*"),
        "org.jetbrains.kotlin.cli.jvm.K2JVMCompiler", "-kotlin-home", kotlin,
        "-jvm-target", "11", "-classpath", runtime, "-d", classes, *sources)
    compiled = ROOT / "build/portable-classes.jar"
    with zipfile.ZipFile(compiled, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(classes.rglob("*.class")):
            archive.write(file, file.relative_to(classes).as_posix())
    d8 = [args.java, "-cp", tools / "r8-stable.jar", "com.android.tools.r8.D8",
          "--min-api", "26", "--release", "--lib", runtime]
    if args.jdk:
        d8 += ["--lib", args.jdk.resolve()]
    run(*d8, "--output", dex, compiled)
    output = ROOT / "patches/build/libs" / f"patches-{version}.mpp"
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "Manifest-Version": "1.0", "Name": "LaKaka patches - Instapaper diagnostics fork",
        "Description": "Local premium flags and optional AI speech HTTP diagnostics",
        "Version": version, "Source": "https://github.com/Kostazk/LaKakaShitPatches",
        "Author": "LaKakaReal; Kostazk", "License": "GPLv3", "Patcher-Version": "2.4.0",
    }
    with zipfile.ZipFile(tools / "patches-1.3.1.mpp") as base, \
            zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as bundle:
        for entry in base.infolist():
            if entry.filename == "META-INF/MANIFEST.MF" or entry.filename == "classes.dex":
                continue
            if entry.filename.startswith("app/template/patches/") and entry.filename.endswith(".class"):
                continue
            if entry.filename == "META-INF/patches.kotlin_module":
                continue
            bundle.writestr(entry, base.read(entry.filename))
        bundle.writestr("META-INF/MANIFEST.MF",
                        "\r\n".join(f"{k}: {v}" for k, v in manifest.items()) + "\r\n\r\n")
        for file in sorted(classes.rglob("*")):
            if file.is_file():
                bundle.write(file, file.relative_to(classes).as_posix())
        for file in sorted(dex.glob("*.dex")):
            bundle.write(file, file.name)
    print(output)

if __name__ == "__main__":
    main()
