from django import template

register = template.Library()


@register.filter
def factor_label(value):
    return str(value).replace("_", " ").title()
