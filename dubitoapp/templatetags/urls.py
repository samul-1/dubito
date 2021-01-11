from typing import Optional, Any

from django import urls, template


register = template.Library()


@register.simple_tag(takes_context=True)
def translate_url(context, language: Optional[str]) -> str:
    """Get the absolute URL of the current page for the specified language.

    Usage:
        {% translate_url 'en' %}
    """
    url = context['request'].build_absolute_uri()
    return urls.translate_url(url, language)
