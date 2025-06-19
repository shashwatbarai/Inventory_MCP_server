from typing import Any, Dict, List
import csv
import os
from datetime import datetime
import httpx
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Mount, Route
from mcp.server import Server
import uvicorn

# Initialize FastMCP server with a name
mcp = FastMCP("Inventory Server")
print("MCP server started successfully")

# File paths
PRODUCTS_CSV = os.path.join(os.path.dirname(__file__), "products.csv")
SALES_DATA_CSV = os.path.join(os.path.dirname(__file__), "sales_data.csv")


def read_csv_file(file_path: str) -> List[Dict[str, Any]]:
    """Read data from a CSV file and return as a list of dictionaries."""
    try:
        with open(file_path, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            return list(reader)
    except Exception as e:
        return []


@mcp.tool()
def get_all_products(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Retrieve all products from inventory.

    Args:
        limit: Maximum number of products to return (default: 100)
        offset: Number of products to skip for pagination (default: 0)
    """
    try:
        products = read_csv_file(PRODUCTS_CSV)
        
        # Apply pagination
        paginated_products = products[offset:offset + limit]
        
        return paginated_products
    except Exception as e:
        return []


@mcp.tool()
def get_sales_data() -> List[Dict[str, Any]]:
    """
    Retrieve all sales data.
    """
    try:
        sales_data = read_csv_file(SALES_DATA_CSV)
        return sales_data
    except Exception as e:
        return []


@mcp.tool()
async def get_season() -> Dict[str, Any]:
    """
    Get current seasonal product priorities based on weather/season.
    """
    # Seasonal product categories
    SEASONAL_PRODUCTS = {
        "summer": {
            "high_priority": [
                "fan",
                "air conditioner",
                "ac",
                "cooler",
                "sunscreen",
                "hat",
                "cap",
            ],
            "medium_priority": [
                "shorts",
                "t-shirt",
                "sandals",
                "sunglasses",
                "water bottle",
            ],
            "multiplier": 2.0,  # Increase threshold by 100% for high priority items
        },
        "winter": {
            "high_priority": ["heater", "jacket", "coat", "blanket", "gloves", "scarf"],
            "medium_priority": ["boots", "sweater", "warm clothes", "thermals"],
            "multiplier": 1.8,
        },
        "rainy": {
            "high_priority": ["umbrella", "raincoat", "rain boots", "waterproof"],
            "medium_priority": ["towel", "dryer", "dehumidifier"],
            "multiplier": 2.5,  # Highest priority for rainy season
        },
        "spring": {
            "high_priority": ["allergy medicine", "light jacket", "gardening tools"],
            "medium_priority": ["casual wear", "sneakers"],
            "multiplier": 1.3,
        },
    }
    try:
        # Get current weather/season
        now = datetime.now()
        date = now.strftime("%d/%m/%Y")
        current_month = now.month
        if current_month in [12, 1, 2]:
            current_season = "winter"
        elif current_month in [3, 4, 5]:
            current_season = "summer"
        elif current_month in [6, 7, 8]:
            current_season = "rainy"
        else:
            current_season = "autumn"

        # Get seasonal priorities
        priorities = SEASONAL_PRODUCTS.get(
            current_season, SEASONAL_PRODUCTS[current_season]
        )

        return {
            "current_date": date,
            "current_season": current_season,
            "high_priority_products": priorities["high_priority"],
            "medium_priority_products": priorities["medium_priority"],
            "priority_multiplier": priorities["multiplier"],
            "recommendation": f"Current season is {current_season}. Focus on stocking {', '.join(priorities['high_priority'][:3])} and related items.",
        }

    except Exception as e:
        return {"error": str(e)}


# HTML for the homepage that displays "MCP Server"
async def homepage(request: Request) -> HTMLResponse:
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Inventory MCP Server</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            h1 {
                margin-bottom: 10px;
            }
            button {
                background-color: #f8f8f8;
                border: 1px solid #ccc;
                padding: 8px 16px;
                margin: 10px 0;
                cursor: pointer;
                border-radius: 4px;
            }
            button:hover {
                background-color: #e8e8e8;
            }
            .status {
                border: 1px solid #ccc;
                padding: 10px;
                min-height: 20px;
                margin-top: 10px;
                border-radius: 4px;
                color: #555;
            }
        </style>
    </head>
    <body>
        <h1>Inventory MCP Server</h1>
        
        <p>Server is running correctly!</p>
        
        <button id="connect-button">Connect to SSE</button>
        
        <div class="status" id="status">Connection status will appear here...</div>
        
        <script>
            document.getElementById('connect-button').addEventListener('click', function() {
                // Redirect to the SSE connection page or initiate the connection
                const statusDiv = document.getElementById('status');
                
                try {
                    const eventSource = new EventSource('/sse');
                    
                    statusDiv.textContent = 'Connecting...';
                    
                    eventSource.onopen = function() {
                        statusDiv.textContent = 'Connected to SSE';
                    };
                    
                    eventSource.onerror = function() {
                        statusDiv.textContent = 'Error connecting to SSE';
                        eventSource.close();
                    };
                    
                    eventSource.onmessage = function(event) {
                        statusDiv.textContent = 'Received: ' + event.data;
                    };
                    
                    // Add a disconnect option
                    const disconnectButton = document.createElement('button');
                    disconnectButton.textContent = 'Disconnect';
                    disconnectButton.addEventListener('click', function() {
                        eventSource.close();
                        statusDiv.textContent = 'Disconnected';
                        this.remove();
                    });
                    
                    document.body.appendChild(disconnectButton);
                    
                } catch (e) {
                    statusDiv.textContent = 'Error: ' + e.message;
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html_content)


# Create a Starlette application with SSE transport
def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can serve the provided mcp server with SSE."""
    # Create an SSE transport with a path for messages
    sse = SseServerTransport("/messages/")

    # Handler for SSE connections
    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,  # access private method
        ) as (read_stream, write_stream):
            # Run the MCP server with the SSE streams
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    # Create and return the Starlette application
    return Starlette(
        debug=debug,
        routes=[
            Route("/", endpoint=homepage),  # Add the homepage route
            Route("/sse", endpoint=handle_sse),  # Endpoint for SSE connections
            Mount("/messages/", app=sse.handle_post_message),  # Endpoint for messages
        ],
    )


if __name__ == "__main__":
    # Get the underlying MCP server from FastMCP wrapper
    mcp_server = mcp._mcp_server

    import argparse
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Run MCP SSE-based server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    args = parser.parse_args()

    # Create and run the Starlette application
    starlette_app = create_starlette_app(mcp_server, debug=True)
    uvicorn.run(starlette_app, host=args.host, port=args.port)