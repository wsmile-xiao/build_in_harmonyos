import re
import sys
import zipfile


def compact(text):
    return re.sub(r"\s+", " ", text).strip()


def section(source, start_marker, end_marker):
    start = source.find(start_marker)
    end = source.find(end_marker, start + len(start_marker))
    if start < 0 or end <= start:
        raise AssertionError(f"cannot isolate policy branch: {start_marker}")
    return source[start:end]


def check(name, branch, required, forbidden=()):
    branch = compact(branch)
    for expression in required:
        if compact(expression) not in branch:
            raise AssertionError(f"{name}: missing {expression}")
    for expression in forbidden:
        if compact(expression) in branch:
            raise AssertionError(f"{name}: unexpected {expression}")
    print(f"PASS: {name}")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 test_button_policy.py <xpi>")
    with zipfile.ZipFile(sys.argv[1]) as archive:
        background = archive.read("scripts/background.js").decode("utf-8")
    policy = section(
        background,
        "async function getButtonPolicy",
        "async function getCurrentPolicy",
    )

    remote = section(policy, "if (remoteButton === true)", "// Adapt button policy")
    ctrl_shift = section(policy, "// Addon button clicked + both CTRL and SHIFT key", "// Addon button clicked + only CTRL key")
    ctrl = section(policy, "// Addon button clicked + only CTRL key", "// Addon button clicked + only SHIFT key")
    shift = section(policy, "// Addon button clicked + only SHIFT key", "// The last case")
    default = section(policy, "// The last case", "async function getCurrentPolicy") if "async function getCurrentPolicy" in policy else policy[policy.find("// The last case"):]
    mode_map = section(default, "const modeMap", "// return modeMap")

    check("remote-content action enables original HTML, remote content and inline option", remote, [
        "remoteButton === true", 'msgBodyAs: "original"',
        "disableRemoteContent: false",
        "attachmentsInline: ((options.tempInline === true) ? true : null)",
    ])
    check("Ctrl+Shift selects sanitized HTML only", ctrl_shift, [
        'info.modifiers.includes("Ctrl") || info.modifiers.includes("Command")',
        'info.modifiers.includes("Shift")',
        'return { msgBodyAs: "sanitized" }',
    ], ['msgBodyAs: "original"', 'msgBodyAs: "plaintext"'])
    check("Ctrl or Command selects original HTML and remote content", ctrl, [
        'info.modifiers.includes("Ctrl") || info.modifiers.includes("Command")',
        '!(info.modifiers.includes("Shift"))', 'msgBodyAs: "original"',
        "disableRemoteContent: false",
        "attachmentsInline: ((options.tempInline === true) ? true : null)",
    ])
    check("Shift selects plaintext only", shift, [
        'info.modifiers.includes("Shift")',
        '!((info.modifiers.includes("Ctrl") || info.modifiers.includes("Command")))',
        'return { msgBodyAs: "plaintext" }',
    ], ['msgBodyAs: "original"', 'msgBodyAs: "sanitized"'])
    check("configured plaintext mode maps to plaintext", mode_map, [
        '"buttonMode_plaintext": "plaintext"',
    ])
    check("configured sanitized mode maps to sanitized", mode_map, [
        '"buttonMode_sanitized": "sanitized"',
    ])
    check("configured HTML mode maps to original", mode_map, [
        '"buttonMode_html": "original"',
    ])
    check("default policy applies mode, remote-content and inline options", default, [
        'msgBodyAs: modeMap[await getOption("buttonHtmlMode")]',
        "disableRemoteContent: !(options.tempRemoteContent)",
        "attachmentsInline: ((options.tempInline === true) ? true : null)",
    ])
    print("allow-html-temp button policy: 8/8 branch-scoped contract tests passed")


if __name__ == "__main__":
    main()
