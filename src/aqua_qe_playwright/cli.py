from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from rich.console import Console
from rich.panel import Panel

from aqua_qe_playwright.config import AQuAConfig
from aqua_qe_playwright.dom_registry import DomKnowledgeRegistry
from aqua_qe_playwright.prompt_builder import AQuAPromptBuilder
from aqua_qe_playwright.story_registry import register_story_artifacts
from aqua_qe_playwright.validator import validate_ppom_chain, validate_knowledge_consistency

console = Console()

BANNER = """\
[bold cyan]AQuA-QE Playwright[/] [dim]v0.1.0[/]
[dim]Artificial Quality Assurance -- Quality Engineering · Playwright[/]
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aqua-qe-playwright",
        description="AQuA-QE Playwright — Assistente de Quality Engineering para Playwright",
    )
    parser.add_argument("--project", default=None, metavar="PROJETO")
    parser.add_argument("--knowledge-root", default=None, metavar="PATH")

    sub = parser.add_subparsers(dest="command", metavar="COMANDO")

    ctx = sub.add_parser("context", help="Gera contexto para análise ou geração de testes")
    ctx.add_argument("--story-id", default="", metavar="ID")
    ctx.add_argument("--story-file", metavar="ARQUIVO")
    ctx.add_argument("--story", metavar="TEXTO")
    ctx.add_argument("--module", default="", metavar="MODULO")
    ctx.add_argument("--task", default="analyze", choices=["analyze", "generate"])
    ctx.add_argument("--copy", action="store_true")
    ctx.add_argument("--output", metavar="ARQUIVO")

    dom = sub.add_parser("dom", help="Registra snapshot HTML e gera contexto DOM")
    dom.add_argument("--module", required=True, metavar="MODULO")
    dom.add_argument("--html-file", required=True, metavar="ARQUIVO")
    dom.add_argument("--story-id", default="", metavar="ID")

    know = sub.add_parser("knowledge", help="Exibe ou consulta a base de conhecimento")
    know.add_argument("--scope", default="all", choices=["modules", "stories", "rules", "dom", "all"])
    know.add_argument("--query", default="", metavar="CONSULTA")

    reg = sub.add_parser("register", help="Registra uma história Jira na base de conhecimento")
    reg.add_argument("--story-id", required=True, metavar="ID")
    reg.add_argument("--module", required=True, metavar="MODULO")
    reg.add_argument("--title", required=True, metavar="TITULO")
    reg.add_argument("--tags", default="", metavar="TAG1,TAG2")

    val = sub.add_parser("validate", help="Valida cadeia PPOM e consistência da base")
    val.add_argument("--target", default="", metavar="PATH", help="Raiz do projeto Playwright")
    val.add_argument("--module", default="", metavar="MODULO")
    val.add_argument("--scope", default="all", choices=["ppom", "knowledge", "all"])

    return parser


def _make_config(args: argparse.Namespace) -> AQuAConfig:
    return AQuAConfig.from_project(
        project=getattr(args, "project", None),
        knowledge_root=getattr(args, "knowledge_root", None),
    )


def cmd_context(args: argparse.Namespace, config: AQuAConfig) -> None:
    story_text = _read_story_text(args)
    if not story_text:
        console.print("[bold red]Erro:[/] Forneça o texto via --story, --story-file ou --story-id.")
        sys.exit(1)
    builder = AQuAPromptBuilder(config.knowledge_root)
    prompt = builder.story_context(
        story_text=story_text,
        story_id=getattr(args, "story_id", ""),
        module=getattr(args, "module", ""),
        task=args.task,
    )
    output_file = getattr(args, "output", None)
    if output_file:
        _save_prompt(prompt, Path(output_file))
    else:
        _display_prompt(prompt, title=f"Contexto AQuA-QE Playwright — {args.task}")
    if getattr(args, "copy", False):
        _copy_to_clipboard(prompt)


def cmd_dom(args: argparse.Namespace, config: AQuAConfig) -> None:
    html_path = Path(args.html_file)
    if not html_path.exists():
        console.print(f"[bold red]Arquivo não encontrado:[/] {html_path}")
        sys.exit(1)
    html_content = html_path.read_text(encoding="utf-8", errors="replace")
    registry = DomKnowledgeRegistry(config.knowledge_root)
    previous_contract = registry.load_current_contract(args.module)
    with console.status("[cyan]Registrando snapshot DOM...[/]", spinner="dots"):
        result = registry.register_snapshot(
            module=args.module,
            html=html_content,
            source_label="aqua-qe-playwright-cli",
            story_id=args.story_id or None,
        )
    console.print(f"[green]OK[/] Snapshot registrado: [bold]{result.change_id}[/]")
    if result.diff_path:
        console.print(f"[yellow]~[/] Diff gerado: {result.diff_path}")
    for w in result.warnings:
        console.print(f"[yellow]![/] {w}")
    builder = AQuAPromptBuilder(config.knowledge_root)
    prompt = builder.dom_context(
        module=args.module,
        html_snippet=html_content,
        story_id=args.story_id,
        previous_contract=previous_contract,
    )
    console.print()
    _display_prompt(prompt, title=f"Contexto DOM — {args.module}")


def cmd_knowledge(args: argparse.Namespace, config: AQuAConfig) -> None:
    builder = AQuAPromptBuilder(config.knowledge_root)
    if args.query:
        prompt = builder.knowledge_context(query=args.query, scope=args.scope)
        _display_prompt(prompt, title="Consulta Knowledge")
    else:
        knowledge = builder._load_knowledge(scope=args.scope)
        if knowledge:
            console.print(Panel(knowledge, title="[bold cyan]Base de Conhecimento[/]", border_style="cyan"))
        else:
            console.print("[yellow]Base de conhecimento vazia ou não encontrada.[/]")


def cmd_register(args: argparse.Namespace, config: AQuAConfig) -> None:
    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else None
    with console.status("[cyan]Registrando história...[/]", spinner="dots"):
        result = register_story_artifacts(
            knowledge_root=config.knowledge_root,
            story_id=args.story_id,
            module=args.module,
            title=args.title,
            tags=tags,
        )
    if result.created:
        console.print("[bold green]Criados:[/]")
        for f in result.created:
            console.print(f"  [green]+[/] {f}")
    if result.updated:
        console.print("[bold yellow]Atualizados:[/]")
        for f in result.updated:
            console.print(f"  [yellow]~[/] {f}")
    if result.skipped:
        console.print("[dim]Ignorados (já existiam):[/]")
        for f in result.skipped:
            console.print(f"  = {f}")


def cmd_validate(args: argparse.Namespace, config: AQuAConfig) -> None:
    scope = args.scope
    all_errors: list[str] = []
    if scope in ("ppom", "all"):
        if not args.target or not args.module:
            console.print("[yellow]![/] --target e --module necessários para validar PPOM. Pulando.")
        else:
            result = validate_ppom_chain(Path(args.target), args.module)
            if result.ok:
                console.print("[bold green]OK PPOM:[/] cadeia válida.")
            else:
                console.print("[bold red]ERRO PPOM — erros:[/]")
                for e in result.errors:
                    console.print(f"  [red]-[/] {e}")
                all_errors.extend(result.errors)
    if scope in ("knowledge", "all"):
        result = validate_knowledge_consistency(config.knowledge_root)
        if result.ok:
            console.print("[bold green]OK Knowledge:[/] base consistente.")
        else:
            console.print("[bold red]ERRO Knowledge — erros:[/]")
            for e in result.errors:
                console.print(f"  [red]-[/] {e}")
            all_errors.extend(result.errors)
    if not all_errors:
        console.print("\n[bold green]OK Tudo validado com sucesso.[/]")
    else:
        console.print(f"\n[bold red]{len(all_errors)} erro(s) encontrado(s).[/]")
        sys.exit(1)


def _display_prompt(prompt: str, title: str = "Prompt AQuA-QE Playwright") -> None:
    console.print()
    console.print(Panel("[dim]Cole o conteúdo abaixo no chat para continuar.[/]",
                        title=f"[bold cyan]{title}[/]", border_style="cyan"))
    console.print()
    sys.stdout.buffer.write((prompt + "\n").encode("utf-8"))
    sys.stdout.buffer.flush()
    console.print()
    console.print(f"[dim]Tamanho do prompt: {len(prompt):,} caracteres[/]")


def _save_prompt(prompt: str, output_path: Path) -> None:
    output_path.write_text(prompt, encoding="utf-8")
    console.print(f"[bold green]OK[/] Prompt salvo em: [bold]{output_path}[/]")
    console.print(f"[dim]Tamanho: {len(prompt):,} caracteres ({output_path.stat().st_size / 1024:.1f} KB)[/]")


def _copy_to_clipboard(text: str) -> None:
    try:
        import pyperclip  # type: ignore
        pyperclip.copy(text)
        console.print("[green]OK[/] Prompt copiado para o clipboard.")
    except ImportError:
        console.print("[yellow]![/] pyperclip não instalado. Instale com: pip install pyperclip")


def _read_story_text(args: argparse.Namespace) -> str:
    text = getattr(args, "story", None) or ""
    if text:
        return text
    file_path = getattr(args, "story_file", None)
    if file_path:
        p = Path(file_path)
        if not p.exists():
            console.print(f"[bold red]Arquivo não encontrado:[/] {p}")
            sys.exit(1)
        return p.read_text(encoding="utf-8")
    story_id = getattr(args, "story_id", "")
    if story_id:
        config_root = _make_config(args).knowledge_root
        story_file = config_root / "stories" / f"{story_id.upper()}.md"
        if story_file.exists():
            return story_file.read_text(encoding="utf-8")
        console.print(
            f"[yellow]![/] História {story_id} não encontrada em {story_file}. "
            "Forneça o texto via --story ou --story-file."
        )
    return ""


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    if not args.command:
        console.print(BANNER)
        parser.print_help()
        sys.exit(0)
    config = _make_config(args)
    dispatch = {
        "context": lambda: cmd_context(args, config),
        "dom": lambda: cmd_dom(args, config),
        "knowledge": lambda: cmd_knowledge(args, config),
        "register": lambda: cmd_register(args, config),
        "validate": lambda: cmd_validate(args, config),
    }
    dispatch[args.command]()


if __name__ == "__main__":
    main()
