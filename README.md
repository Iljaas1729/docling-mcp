# Docling-MCP Fork: File-Based Document Conversion

This is a personal fork of the `docling-project/docling-mcp` repository, streamlined for file-based document conversion workflows.

## Purpose

The primary goal of this fork is to provide a stable and focused version of the Docling MCP server optimized for command-line and LLM-based workflows. By focusing exclusively on tools that convert and **save documents directly to the filesystem**, it avoids the need for inline parsing of large, converted files within a terminal session. This makes it ideal for batch processing and interacting with local files in an automated agentic setting.

## Core Tools

This server provides two main tools focused on file-based conversion:

*   **`convert_to_markdown`**: Converts one or more documents from local file paths or URLs into Markdown files, saving them to disk.
*   **`convert_html_to_markdown`**: Scans a local folder for HTML files and converts only those that do not already have a corresponding Markdown file, saving the new files to disk.

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
