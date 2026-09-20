"""Interactive Rich CLI console for StrandsOps.

Run with: python -m strandops.cli
"""
from __future__ import annotations

import sys
from strandops.simulator.cloud import cloud
from strandops.simulator.models import ChaosScenario


def main() -> None:
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        from rich.table import Table
        from rich.markdown import Markdown
    except ImportError:
        print("[ERROR] 'rich' is required. Run: pip install rich")
        sys.exit(1)

    from strandops.agent import create_sre_agent, get_provider_info

    console = Console()
    info = get_provider_info()

    status_color = "green" if info["has_credentials"] else "yellow"

    console.print(Panel(
        Text.from_markup(
            "[bold red]🛡️  STRANDSOPS — AUTONOMOUS CLOUD SRE CONSOLE[/bold red]\n"
            "[dim]Powered by Strands Agents SDK & Amazon Bedrock (AWS)[/dim]\n\n"
            f"[bold cyan]☁️  AWS Cloud Service:[/bold cyan] Amazon Bedrock\n"
            f"[bold cyan]🆔 AWS Account ID:[/bold cyan] [white]{info['account_id']}[/white]\n"
            f"[bold cyan]🤖 Bedrock Model:[/bold cyan] [white]{info['model_id']}[/white]\n"
            f"[bold cyan]📍 AWS Region:[/bold cyan] [white]{info['region']}[/white]\n"
            f"[bold cyan]🔑 Bedrock Status:[/bold cyan] [{status_color}]{info['status']}[/{status_color}]\n\n"
            "[bold white]Available Commands:[/bold white]\n"
            "• [cyan]chaos 1[/cyan] : Inject SQS Poison-Pill Storm\n"
            "• [cyan]chaos 2[/cyan] : Inject Payment Gateway Memory Leak (OOM)\n"
            "• [cyan]chaos 3[/cyan] : Inject Misconfigured API Rate Limiter\n"
            "• [cyan]chaos 4[/cyan] : Inject DB Connection Pool Starvation\n"
            "• [cyan]status[/cyan]  : Print live telemetry table\n"
            "• [cyan]reset[/cyan]   : Restore cloud to healthy baseline\n"
            "• [cyan]exit[/cyan]    : Quit console\n"
            "Or simply type your prompt in natural language!"
        ),
        border_style="red",
        padding=(1, 2),
    ))

    def print_status_table():
        table = Table(title="Live Cloud Infrastructure Telemetry", border_style="cyan")
        table.add_column("Service", style="bold white")
        table.add_column("Status", justify="center")
        table.add_column("P99 Latency", justify="right")
        table.add_column("Error Rate", justify="right")
        table.add_column("Memory", justify="right")

        for t in cloud.get_telemetry():
            status_style = "green" if t.status.value == "healthy" else "bold red"
            table.add_row(
                t.service_name,
                f"[{status_style}]{t.status.value.upper()}[/{status_style}]",
                f"{t.p99_latency_ms:.0f} ms",
                f"{t.error_rate_pct:.1f}%",
                f"{t.memory_usage_mb:.0f} MB",
            )
        console.print(table)

    agent = create_sre_agent()

    while True:
        try:
            user_input = console.input("[bold yellow]StrandsOps> [/bold yellow]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting StrandsOps console. Keep your clusters green! 👋[/dim]")
            break

        if not user_input:
            continue

        cmd = user_input.lower()
        if cmd in ("exit", "quit", "q"):
            console.print("[dim]Exiting StrandsOps console. Keep your clusters green! 👋[/dim]")
            break

        elif cmd == "status":
            print_status_table()
            continue

        elif cmd == "reset":
            cloud.reset()
            console.print("[green]Cloud infrastructure restored to baseline healthy state.[/green]")
            continue

        elif cmd == "chaos 1":
            inc = cloud.inject_chaos(ChaosScenario.SQS_POISON_PILL)
            console.print(f"[bold red]🚨 Injected SQS Poison Pill Storm! (Incident {inc.incident_id})[/bold red]")
            print_status_table()
            user_input = "An SQS poison pill alert was just detected. Investigate the failure, verify safety, execute remediation, and verify recovery."

        elif cmd == "chaos 2":
            inc = cloud.inject_chaos(ChaosScenario.MEMORY_LEAK_OOM)
            console.print(f"[bold red]🚨 Injected Payment Gateway Memory Leak! (Incident {inc.incident_id})[/bold red]")
            print_status_table()
            user_input = "Payment Gateway memory is leaking and latency breached 3000ms. Diagnose and remediate."

        elif cmd == "chaos 3":
            inc = cloud.inject_chaos(ChaosScenario.RATE_LIMIT_MISCONFIG)
            console.print(f"[bold red]🚨 Injected Bad Rate-Limit Deployment! (Incident {inc.incident_id})[/bold red]")
            print_status_table()
            user_input = "API Gateway is returning 429 Too Many Requests to clients. Investigate and restore service."

        elif cmd == "chaos 4":
            inc = cloud.inject_chaos(ChaosScenario.DB_CONNECTION_STARVATION)
            console.print(f"[bold red]🚨 Injected DB Connection Pool Starvation! (Incident {inc.incident_id})[/bold red]")
            print_status_table()
            user_input = "Order Service database connection pool is starved. Diagnose root cause, check blast radius, and remediate."

        # Pass prompt to Strands agent
        console.print("\n[dim]StrandsOps agent reasoning...[/dim]")
        try:
            response = agent(user_input)
            reply = ""
            if hasattr(response, "message") and hasattr(response.message, "content"):
                for block in response.message.content:
                    if hasattr(block, "text"):
                        reply += block.text
            if not reply:
                reply = str(response)

            console.print(Panel(
                Markdown(reply),
                title="[bold green]StrandsOps Resolution[/bold green]",
                border_style="green",
                padding=(1, 2),
            ))
        except Exception as e:
            err_type = type(e).__name__
            if "NoCredentialsError" in err_type or "credentials" in str(e).lower():
                console.print(
                    "[bold yellow]⚠️  AWS Bedrock Credentials Required:[/bold yellow] "
                    "Configure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env, "
                    "or set MODEL_PROVIDER=ollama for offline testing."
                )
            else:
                console.print(f"[bold red]Execution error ({err_type}):[/bold red] {e}")


if __name__ == "__main__":
    main()
