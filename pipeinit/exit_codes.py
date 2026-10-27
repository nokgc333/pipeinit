"""終了コードの定義と、文書・`--help` に載せる表(仕様書_v2.md §5.4)。"""

from __future__ import annotations

EXIT_OK = 0
EXIT_VIOLATIONS_OR_RULE_ERROR = 1
EXIT_USAGE = 2
EXIT_NOT_WRITABLE = 5
EXIT_PATH_TRAVERSAL = 6
EXIT_RENAME_CONFLICT = 7

EXIT_CODE_TABLE: tuple[tuple[int, str, str], ...] = (
    (EXIT_OK, "OK(違反なし・処理に成功)", "success, no violations"),
    (
        EXIT_VIOLATIONS_OR_RULE_ERROR,
        "命名の違反あり、またはルールファイルの誤り",
        "violations found, or a rule file error",
    ),
    (EXIT_USAGE, "使い方の誤り(引数・オプション)", "usage error (arguments or options)"),
    (EXIT_NOT_WRITABLE, "書き込めない(権限・作成先)", "cannot write (permissions or destination)"),
    (
        EXIT_PATH_TRAVERSAL,
        "ルールのパスが、作成先の外を指している",
        "a rule path escapes the target directory",
    ),
    (
        EXIT_RENAME_CONFLICT,
        "リネーム先に、同名のファイルがある",
        "the rename destination already exists",
    ),
)


def exit_code_help(lang: str) -> str:
    """`--help` の末尾に出す、終了コードの表。"""
    index = 1 if lang == "ja" else 2
    title = "終了コード:" if lang == "ja" else "Exit codes:"
    rows = "\n".join(f"  {row[0]}  {row[index]}" for row in EXIT_CODE_TABLE)
    return f"\b\n{title}\n{rows}"
