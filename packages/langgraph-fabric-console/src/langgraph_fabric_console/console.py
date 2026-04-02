"""Console interaction surface."""

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph_fabric_core.graph.orchestrator import AgentOrchestrator
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


async def run_console(orchestrator: AgentOrchestrator) -> None:
    """Run interactive terminal chat with streamed responses."""
    # Welcome message
    welcome_text = Text("LangGraph Fabric MCP Console", style="bold cyan")
    console.print(
        Panel(
            welcome_text,
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
                user_id="console-user",
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
