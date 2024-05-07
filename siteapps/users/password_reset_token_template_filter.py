from urllib.parse import parse_qs, urlparse

from django import template

register = template.Library()


@register.filter(name="extract_token")
def extract_token(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    token = query_params.get("token", [None])[0]
    return token
