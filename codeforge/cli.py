import click
from .orchestrator import ReviewOrchestrator
from .config import load_config
from .models import PRContext

@click.group()
def main():
    """CodeForge Review Command Line Interface."""
    pass

@main.command()
@click.option("--repo", required=True, help="The repository in 'owner/repo' format.")
@click.option("--pr", type=int, required=True, help="The pull request number.")
@click.option("--reviewers", default="all", help="Comma-separated list of reviewers to run.")
@click.option("--output", type=click.Choice(["terminal", "json", "github"]), default="terminal",
              help="Output format.")
def review(repo, pr, reviewers, output):
    """Review a pull request."""
    config = load_config()
    orchestrator = ReviewOrchestrator(config)

    try:
        consensus_result = orchestrator.review_pr(repo, pr)
        
        if output == "terminal":
            click.echo(format_terminal(consensus_result))
        elif output == "json":
            click.echo(format_json(consensus_result))
        elif output == "github":
            click.echo(format_github_review(consensus_result))
    except Exception as e:
        click.echo(f"Error during review: {e}", err=True)

@main.command()
def config():
    """Show current configuration."""
    config = load_config()
    click.echo(f"Reviewers: {config.reviewers}")
    click.echo(f"LLM Provider: {config.llm_provider}")
    click.echo(f"LLM Model: {config.llm_model}")
    click.echo(f"Max Findings: {config.max_findings}")
    click.echo(f"Severity Threshold: {config.severity_threshold}")

@main.command()
def version():
    """Show the version of CodeForge Review."""
    click.echo("CodeForge Review version 1.0.0")  # Replace with actual version if available

if __name__ == "__main__":
    main()