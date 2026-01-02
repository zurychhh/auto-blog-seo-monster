"""
Token counter for Claude API usage tracking.
Uses tiktoken for approximate token counting.
"""

import tiktoken
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class TokenCounter:
    """Token counter using tiktoken (approximate for Claude)."""

    def __init__(self, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize token counter.

        Note: Claude uses a different tokenizer than OpenAI, but tiktoken
        provides a good approximation for billing purposes.
        """
        self.model = model
        # Use cl100k_base encoding as approximation for Claude
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Approximate token count
        """
        try:
            tokens = self.encoding.encode(text)
            return len(tokens)
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            # Fallback: approximate 1 token ≈ 4 characters
            return len(text) // 4

    def count_messages_tokens(self, messages: list[dict[str, str]]) -> int:
        """
        Count tokens in a list of messages.

        Args:
            messages: List of messages with 'role' and 'content'

        Returns:
            Approximate total token count
        """
        total = 0
        for message in messages:
            # Count content tokens
            content = message.get("content", "")
            total += self.count_tokens(content)

            # Add overhead for message structure (~4 tokens per message)
            total += 4

        # Add overhead for message structure
        total += 3  # Every reply is primed with <|start|>assistant<|message|>

        return total

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost for Claude API call.

        Pricing (as of 2024):
        - Claude 3.5 Sonnet: $3/1M input, $15/1M output tokens

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        # Prices per 1M tokens
        input_price_per_m = 3.0
        output_price_per_m = 15.0

        input_cost = (input_tokens / 1_000_000) * input_price_per_m
        output_cost = (output_tokens / 1_000_000) * output_price_per_m

        return input_cost + output_cost


# Global instance
_token_counter: Optional[TokenCounter] = None


def get_token_counter() -> TokenCounter:
    """Get global token counter instance."""
    global _token_counter
    if _token_counter is None:
        _token_counter = TokenCounter()
    return _token_counter


def count_tokens(text: str) -> int:
    """
    Helper function to count tokens in text.

    Args:
        text: Text to count

    Returns:
        Token count
    """
    counter = get_token_counter()
    return counter.count_tokens(text)
