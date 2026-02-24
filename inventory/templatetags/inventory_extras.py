from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def query_string(context, **kwargs):
    """Build query string from current GET params, overriding specified keys."""
    request = context["request"]
    params = request.GET.copy()
    for key, value in kwargs.items():
        if value is not None and value != "":
            params[key] = value
        elif key in params:
            del params[key]
    return params.urlencode()


@register.simple_tag(takes_context=True)
def page_url(context, page_num):
    """Build URL for pagination preserving all GET params except page."""
    request = context["request"]
    params = request.GET.copy()
    params["page"] = page_num
    return "?" + params.urlencode()


@register.simple_tag(takes_context=True)
def sort_url(context, field):
    """Build sort URL for a column: toggles asc/desc when clicking same column."""
    request = context["request"]
    current_sort = request.GET.get("sort", "name")
    current_order = request.GET.get("order", "asc")
    params = request.GET.copy()
    params["sort"] = field
    if current_sort == field:
        params["order"] = "desc" if current_order == "asc" else "asc"
    else:
        params["order"] = "asc"
    return "?" + params.urlencode()
