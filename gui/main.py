#!/usr/bin/env python3
"""
Lab Workflow GUI - Main Entry Point
Starts the NiceGUI app for processing video experiments
"""

import logging
import asyncio
from nicegui import ui
from gui_components import create_main_interface

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@ui.page("/")
async def index():
    """Main page with the workflow interface"""
    ui.add_head_html(
        """
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }
        .nicegui-content { 
            padding: 0; 
        }
    </style>
    """
    )

    await create_main_interface()


if __name__ in {"__main__", "__mp_main__"}:
    # Configure NiceGUI
    ui.run(
        title="🧠 Lab Workflow Manager",
        port=8080,
        show=True,
        reload=False,
        favicon="🧠",
        dark=False,
    )
