"""Console interaction surface."""

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph_fabric_core.core.config import CoreSettings
from langgraph_fabric_core.graph.orchestrator import AgentOrchestrator
from langgraph_fabric_core.mcp.auth import TokenProvider
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


async def run_console(
    orchestrator: AgentOrchestrator,
    settings: CoreSettings,
    token_provider: TokenProvider,
) -> None:
    """Run interactive terminal chat with streamed responses."""
    if settings.mcp_servers:
        identity = token_provider.get_authenticated_identity(settings.mcp_servers[0].scope)
        user_id = identity.user_id
        tenant_info = identity.tenant_id
        if tenant_info == "unknown":
            tenant_info = (
                settings.microsoft_tenant_id if settings.microsoft_tenant_id else "default"
            )
        connection_info = Text(
            f"Tenant: {tenant_info}\nUser ID: {user_id}",
            style="dim cyan",
        )
    else:
        user_id = "local-user"
        connection_info = Text(
            "Mode: chat-only\nMCP servers: none configured",
            style="dim cyan",
        )

    # Welcome message
    welcome_text = Text("LangGraph MCP Console", style="bold cyan")

    # Combine welcome and connection info
    welcome_panel_text = Text()
    welcome_panel_text.append(welcome_text)
    welcome_panel_text.append("\n\n")
    welcome_panel_text.append(connection_info)

    console.print(
        Panel(
            welcome_panel_text,
            title="[bold green]✨ Welcome[/bold green]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print("[dim yellow]Press Enter on empty input to exit.[/dim yellow]\n")

    history: list[BaseMessage] = []
    message_count = 0

    while True:
        # User input with styled prompt
        user_input_text = console.input("[bold blue]You:[/bold blue] ")
        if not user_input_text.strip():
            break

        prompt = user_input_text

        # Stream response with spinning status
        chunks: list[str] = []
        assistant_text = Text()

        with console.status("[yellow]Thinking...[/yellow]", spinner="dots") as status:
            async for chunk in orchestrator.stream(
                prompt=prompt,
                channel="console",
                auth_mode="local",
                user_id=user_id,
                mcp_user_tokens={},
                history=history,
            ):
                # Check if this is a tool call message
                if chunk.startswith("\n[tool]"):
                    # Print tool notification outside the status spinner
                    status.stop()
                    console.print(chunk.strip(), style="dim yellow")
                    status.start()
                else:
                    # Regular text chunk - append to response
                    chunks.append(chunk)
                    assistant_text.append(chunk)
                    # Update status to show progress
                    if chunks:
                        status.update("[yellow]Generating response...[/yellow]")

        # Print the complete assistant response in a panel
        console.print(
            Panel(
                assistant_text,
                title="[bold green]Assistant Response[/bold green]",
                border_style="green",
                padding=(1, 2),
            )
        )

        # Update history
        history.append(HumanMessage(content=prompt))
        history.append(AIMessage(content="".join(chunks)))

        # Show conversation stats
        message_count += 1
        console.print(
            f"[dim cyan]Messages: {message_count} | History: {len(history)} turns[/dim cyan]\n"
        )

    # Goodbye message
    console.print(
        Panel(
            Text("Thank you for using LangGraph Fabric Console!", style="bold cyan"),
            title="[bold yellow]👋 Goodbye[/bold yellow]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
