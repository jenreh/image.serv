"""Adaptive Card generation utilities for image responses.

Creates Microsoft Adaptive Card JSON for rendering images in compatible clients.
Reference: https://adaptivecards.microsoft.com/
"""

import json
import logging

logger = logging.getLogger(__name__)


def image_card(
    prompt: str,
    image_url: str,
) -> str:
    """Create Adaptive Card JSON for generated images."""
    card = {
        "type": "AdaptiveCard",
        "$schema": "https://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "layouts": [
            {
                "type": "Layout.AreaGrid",
                "areas": [
                    {"name": "imageArea"},
                    {"name": "labelArea", "row": 2},
                    {"name": "promptArea", "row": 3},
                ],
            }
        ],
        "body": [
            {
                "type": "Image",
                "url": image_url,
                "grid.area": "imageArea",
                "altText": prompt,
                "spacing": "None",
                "style": "RoundedCorners",
            },
            {
                "type": "TextBlock",
                "text": "Prompt",
                "weight": "Bolder",
                "grid.area": "labelArea",
            },
            {
                "type": "TextBlock",
                "text": prompt,
                "wrap": True,
                "grid.area": "promptArea",
            },
        ],
        "fallbackText": f"Generated Image: {prompt}",
        "speak": prompt,
        "selectAction": {
            "type": "Action.OpenUrl",
            "url": image_url,
        },
    }

    return json.dumps(card, indent=2)
