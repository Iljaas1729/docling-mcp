"""Tools for converting documents into DoclingDocument objects."""

import gc
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Optional

from mcp.server.fastmcp import Context
from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, ErrorData, ToolAnnotations
from pydantic import Field

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
)
from docling.document_converter import DocumentConverter, FormatOption, PdfFormatOption
from docling_core.types.doc.document import (
    ContentLayer,
)
from docling_core.types.doc.labels import (
    DocItemLabel,
)

from docling_mcp.docling_cache import get_cache_key
from docling_mcp.logger import setup_logger
from docling_mcp.settings.conversion import settings
from docling_mcp.shared import local_document_cache, local_stack_cache, mcp

# Create a default project logger
logger = setup_logger()


def cleanup_memory() -> None:
    """Force garbage collection to free up memory."""
    logger.info("Performed memory cleanup")
    gc.collect()


@dataclass
class IsDoclingDocumentInCacheOutput:
    """Output of the is_document_in_local_cache tool."""

    in_cache: Annotated[
        bool,
        Field(
            description=(
                "Whether the document is already converted and in the local cache."
            )
        ),
    ]


# @mcp.tool(
#     title="Is Docling document in cache",
#     annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False),
# )
def is_document_in_local_cache(
    document_key: Annotated[
        str,
        Field(description="The unique identifier of the document in the local cache."),
    ],
) -> IsDoclingDocumentInCacheOutput:
    """Verify if a Docling document is already converted and in the local cache."""
    return IsDoclingDocumentInCacheOutput(document_key in local_document_cache)


@dataclass
class ConvertDocumentOutput:
    """Output of the convert_document_into_docling_document tool."""

    from_cache: Annotated[
        bool,
        Field(
            description=(
                "Whether the document was already converted in the local cache."
            )
        ),
    ]
    document_key: Annotated[
        str,
        Field(description="The unique identifier of the document in the local cache."),
    ]


@lru_cache
def _get_converter() -> DocumentConverter:
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = settings.do_ocr
    pipeline_options.generate_page_images = settings.keep_images
    
    # Configure threading
    if hasattr(settings, 'num_threads'):
        pipeline_options.accelerator_options.num_threads = settings.num_threads
    
    # Configure OCR options
    if hasattr(settings, 'force_full_page_ocr') and settings.force_full_page_ocr:
        pipeline_options.ocr_options.force_full_page_ocr = True
    
    if hasattr(settings, 'ocr_confidence_threshold'):
        pipeline_options.ocr_options.confidence_threshold = settings.ocr_confidence_threshold

    format_options: dict[InputFormat, FormatOption] = {
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        InputFormat.IMAGE: PdfFormatOption(pipeline_options=pipeline_options),
    }

    logger.info(f"Creating DocumentConverter with format_options: {format_options}")
    return DocumentConverter(format_options=format_options)


# @mcp.tool(
#     title="Convert document into Docling document",
#     annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
# )
def convert_document_into_docling_document(
    source: Annotated[
        str,
        Field(description="The URL or local file path to the document."),
    ],
) -> ConvertDocumentOutput:
    """Convert a document of any type from a URL or local path and store in local cache.

    This tool takes a document's URL or local file path, converts it using
    Docling's DocumentConverter, and stores the resulting Docling document in a
    local cache. It returns an output with a boolean set to False along with the
    document's unique cache key. If the document was already in the local cache,
    the conversion is skipped and the output boolean is set to True.
    """
    try:
        # Remove any quotes from the source string
        source = source.strip("\"'")

        # Log the cleaned source
        logger.info(f"Processing document from source: {source}")

        # Generate cache key
        cache_key = get_cache_key(source)

        if cache_key in local_document_cache:
            logger.info(f"{source} has previously been added.")
            return ConvertDocumentOutput(True, cache_key)

        # Get converter
        converter = _get_converter()

        # Convert the document
        logger.info("Start conversion")
        result = converter.convert(source)

        # Check for errors - handle different API versions
        has_error = False
        error_message = ""

        # Try different ways to check for errors based on the API version
        if hasattr(result, "status"):
            if hasattr(result.status, "is_error"):
                has_error = result.status.is_error
            elif hasattr(result.status, "error"):
                has_error = result.status.error

        if hasattr(result, "errors") and result.errors:
            has_error = True
            error_message = str(result.errors)

        if has_error:
            error_msg = f"Conversion failed: {error_message}"
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=error_msg))

        local_document_cache[cache_key] = result.document

        item = result.document.add_text(
            label=DocItemLabel.TEXT,
            text=f"source: {source}",
            content_layer=ContentLayer.FURNITURE,
        )

        local_stack_cache[cache_key] = [item]

        # Log completion
        logger.info(f"Successfully created the Docling document: {source}")

        # Clean up memory
        cleanup_memory()

        return ConvertDocumentOutput(False, cache_key)

    except Exception as e:
        logger.exception(f"Error converting document: {source}")
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message=f"Unexpected error: {e!s}")
        ) from e


@dataclass
class ConvertToMarkdownOutput:
    """Output of the convert_to_markdown tool."""

    output_files: Annotated[
        list[str],
        Field(description="A list of file paths to the generated Markdown files."),
    ]


@mcp.tool(title="Convert one or more documents to Markdown")
async def convert_to_markdown(
    sources: Annotated[
        list[str],
        Field(
            description="A list of URLs or absolute file paths to the documents to convert."
        ),
    ],
    ctx: Context,  # type: ignore[type-arg]
    output_folder: Annotated[
        Optional[str],
        Field(
            description=(
                "The absolute file path to the directory where the Markdown files will be saved. "
                "If not provided, for file sources, the output will be in the same directory as the source file. "
                "For URL sources, the output will be in the default directory configured in the server settings."
            )
        ),
    ] = None,
) -> ConvertToMarkdownOutput:
    """Convert one or more documents to Markdown and save them to a folder.

    This tool supports a variety of document formats, including docx, html, pdf, and images.
    It takes a list of document sources (URLs or absolute file paths),
    converts each document to a Docling document, exports it to Markdown,
    and saves it to the specified output folder.
    """
    output_files = []
    converter = _get_converter()
    total_sources = len(sources)

    for i, source in enumerate(sources):
        try:
            source = source.strip("\"'")
            logger.info(f"Processing document from source: {source}")
            await ctx.info(f"Processing source: {source}")
            await ctx.report_progress(i + 1, total_sources)

            current_output_path: Path
            if output_folder:
                current_output_path = Path(output_folder)
            else:
                # Determine output path based on source type
                if Path(source).is_absolute() and Path(source).exists(): # Check if it's a local file path
                    current_output_path = Path(source).parent
                else: # Assume it's a URL or invalid local path, use default
                    current_output_path = Path(settings.default_output_directory)

            current_output_path.mkdir(parents=True, exist_ok=True)

            result = converter.convert(source)
            if hasattr(result, "status") and hasattr(result.status, "is_error") and result.status.is_error:
                error_msg = f"Conversion failed for {source}"
                raise McpError(ErrorData(code=INTERNAL_ERROR, message=error_msg))

            markdown_content = result.document.export_to_markdown()
            file_name = Path(source).stem
            output_file = current_output_path / f"{file_name}.md"
            output_file.write_text(markdown_content, encoding="utf-8")
            output_files.append(str(output_file))
            logger.info(f"Successfully converted {source} to {output_file}")

        except Exception as e:
            logger.exception(f"Error converting document: {source}")
            raise McpError(
                ErrorData(code=INTERNAL_ERROR, message=f"Unexpected error for {source}: {e!s}")
            ) from e

    cleanup_memory()
    return ConvertToMarkdownOutput(output_files=output_files)


# @mcp.tool(
#     title="Convert files from directory into Docling document", structured_output=True
# )
async def convert_directory_files_into_docling_document(
    source: Annotated[
        str,
        Field(description="The path to a local directory"),
    ],
    ctx: Context,  # type: ignore[type-arg]
) -> list[ConvertDocumentOutput]:
    """Convert all files from a local directory path and store them in local cache.

    This tool takes a local directory path, converts every file in the directory using
    Docling's DocumentConverter and stores the resulting Docling documents in a local
    cache. It returns a list of conversion outputs, where each output consists of a
    boolean set to False along with a document's unique cache key. If a document was
    already in the local cache, the conversion is skipped and the output boolean is set
    to True.
    """
    try:
        # Remove any quotes from the source string
        source = source.strip("\"'")
        directory = Path(source)
        files: list[Path] = list(directory.iterdir())
        out: list[ConvertDocumentOutput] = []
        logger.info("Getting the converter")
        converter = _get_converter()

        for i, file in enumerate(files):
            if not file.is_file():
                continue

            # Track progress
            await ctx.info(f"Processing file {file}")
            await ctx.report_progress(i + 1, len(files))

            logger.info(f"Processing file {file}")
            cache_key = get_cache_key(str(file))
            if cache_key in local_document_cache:
                logger.info(f"{file} has been previously converted.")
                out.append(ConvertDocumentOutput(True, cache_key))
            else:
                # Convert the document
                logger.info("Start conversion")
                result = converter.convert(file)
                has_error = False
                error_message = ""
                if hasattr(result, "status"):
                    if hasattr(result.status, "is_error"):
                        has_error = result.status.is_error
                    elif hasattr(result.status, "error"):
                        has_error = result.status.error

                if hasattr(result, "errors") and result.errors:
                    has_error = True
                    error_message = str(result.errors)

                if has_error:
                    error_msg = f"Conversion failed: {error_message}"
                    raise McpError(ErrorData(code=INTERNAL_ERROR, message=error_msg))

                local_document_cache[cache_key] = result.document

                item = result.document.add_text(
                    label=DocItemLabel.TEXT,
                    text=f"source: {file}",
                    content_layer=ContentLayer.FURNITURE,
                )

                local_stack_cache[cache_key] = [item]

                await ctx.debug(
                    f"Completed step {i + 1} with Docling document key: {cache_key}"
                )
                logger.info(f"Successfully created the Docling document: {file}")
                out.append(ConvertDocumentOutput(False, cache_key))

        cleanup_memory()

        return out

    except Exception as e:
        logger.exception(f"Error converting files in directory: {source}")
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message=f"Unexpected error: {e!s}")
        ) from e


@mcp.tool(title="Convert HTML files in a folder to Markdown")
async def convert_html_to_markdown(
    folder_path: Annotated[
        str,
        Field(description="The absolute local file path to the folder to scan."),
    ],
    ctx: Context,  # type: ignore[type-arg]
) -> ConvertToMarkdownOutput:
    """Converts HTML files in a folder to Markdown, skipping existing .md counterparts."""
    try:
        p = Path(folder_path)
        if not p.is_dir():
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR, message=f"Path is not a directory: {folder_path}"
                )
            )

        html_files = list(p.glob("*.html"))
        md_files = {f.stem for f in p.glob("*.md")}

        files_to_convert = [
            str(html_file)
            for html_file in html_files
            if html_file.stem not in md_files
        ]

        if not files_to_convert:
            await ctx.info("No new HTML files to convert.")
            return ConvertToMarkdownOutput(output_files=[])

        await ctx.info(f"Found {len(files_to_convert)} new HTML files to convert.")
        return await convert_to_markdown(
            sources=files_to_convert, ctx=ctx, output_folder=folder_path
        )

    except Exception as e:
        logger.exception(f"Error converting new HTML files in folder: {folder_path}")
        raise McpError(
            ErrorData(code=INTERNAL_ERROR, message=f"Unexpected error: {e!s}")
        ) from e
