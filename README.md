# Docling-MCP Fork: Document Conversion Tools

This is a personal fork of the `docling-project/docling-mcp` repository, streamlined to focus on specific document conversion tasks.

## Purpose

The primary goal of this fork is to provide a stable and focused version of the Docling MCP server that exposes only the `convert_to_markdown` tool. This allows for reliable conversion of various document formats (HTML, PDF, etc.) into Markdown without the overhead of other experimental or unused features.

## Core Tool: `convert_to_markdown`

This server provides one main tool:

*   **`convert_to_markdown`**: Converts one or more documents from local file paths or URLs into Markdown files.

## How to Run This Server

This server is intended to be run locally as an MCP server for clients like Cline. Use the following command from the project root:

```bash
uv run python -m docling_mcp.servers.mcp_server conversion
```

## Syncing with the Upstream Repository

This fork is kept up-to-date with the original `docling-project/docling-mcp` repository. To pull in the latest changes, use the standard `upstream` workflow:

```bash
# Fetch the latest changes from the public repository
git fetch upstream

# Merge the changes into your main branch
git merge upstream/main
