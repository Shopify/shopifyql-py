import logging
import os
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

logger = logging.getLogger(__name__)

DEFAULT_AUTO_CLOSE_DELAY = 2
HTML_AUTH_SUCCESS = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Authentication Success</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                text-align: center;
                max-width: 400px;
            }}
            h1 {{
                color: #2ecc71;
                margin: 0 0 20px 0;
            }}
            #countdown {{
                font-size: 24px;
                font-weight: bold;
                color: #667eea;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Authentication Successful!</h1>
            <p>Closing in <span id="countdown">{auto_close_delay}</span> seconds...</p>
            <p><small>You can return to JupyterLab now</small></p>
        </div>

        <script>
            let seconds = {auto_close_delay};
            const countdownElement = document.getElementById('countdown');

            const interval = setInterval(() => {{
                seconds--;
                countdownElement.textContent = seconds;

                if (seconds <= 0) {{
                    clearInterval(interval);
                    window.close();
                    setTimeout(() => {{
                        window.close();
                    }}, 100);
                    setTimeout(() => {{
                        if (!window.closed) {{
                            document.body.innerHTML = '<div class="container"><h2>You can now close this tab</h2><p>Return to JupyterLab to continue</p></div>';
                        }}
                    }}, 500);
                }}
            }}, 1000);
        </script>
    </body>
    </html>
"""


class ShopifyAuthenticator:
    """
    Authenticate with Shopify using OAuth2.

    Args:
        shop: Shopify shop name
        key: Shopify API key
        secret: Shopify API secret
        port: Port to use for the local server
    """

    def __init__(self, shop: str, key: str, secret: str, port: int = 4545) -> None:
        self._shop = shop
        self._key = key or os.getenv("SHOPIFY_API_KEY")
        self._secret = secret or os.getenv("SHOPIFY_API_SECRET")
        self._port = port

    def authenticate(
        self,
        auto_close_delay: int = DEFAULT_AUTO_CLOSE_DELAY,
    ) -> str | None:
        """
        Authenticate with Shopify using OAuth2.

        Args:
            auto_close_delay: Delay in seconds to close the browser

        Returns:
            Access token
        """
        if not self._key or not self._secret or not self._shop:
            raise ValueError("Shopify API key, secret, and shop are required")

        REDIRECT_URI = f"http://localhost:{self._port}/callback"

        auth_data = {"code": None}

        class ShopifyCallbackHandler(BaseHTTPRequestHandler):
            def do_GET(handler_self):
                query = urlparse(handler_self.path).query
                params = parse_qs(query)

                auth_data["code"] = params.get("code", [None])[0]

                handler_self.send_response(200)
                handler_self.send_header("Content-type", "text/html")
                handler_self.end_headers()

                handler_self.wfile.write(
                    HTML_AUTH_SUCCESS.format(auto_close_delay=auto_close_delay).encode(
                        "utf-8"
                    )
                )

            def log_message(handler_self, format, *args):
                pass

        auth_params = {
            "client_id": self._key,
            "redirect_uri": REDIRECT_URI,
            "state": "nonce",
        }

        authorization_url = f"https://{self._shop}.myshopify.com/admin/oauth/authorize?{urlencode(auth_params)}"

        webbrowser.open(authorization_url)

        server = HTTPServer(("localhost", self._port), ShopifyCallbackHandler)
        server.handle_request()

        auth_code = auth_data["code"]

        # No authorization code received
        if not auth_code:
            logger.error("No authorization code received")
            return None

        # Exchange authorization code for access token
        token_data = {
            "client_id": self._key,
            "client_secret": self._secret,
            "code": auth_code,
        }

        token_response = requests.post(
            f"https://{self._shop}.myshopify.com/admin/oauth/access_token",
            json=token_data,
        )

        if token_response.status_code == 200:
            token_info = token_response.json()
            token = token_info["access_token"]
            return token
        else:
            logger.error(f"Token exchange failed: {token_response.text}")
            return None
