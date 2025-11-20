import os
from django import template

register = template.Library()

@register.filter
def file_exists(file_field):
    """
    Check if a given file actually exists in the media folder.
    Used in templates like {{ offer.file|file_exists }}
    """
    try:
        if not file_field:
            return False
        return os.path.exists(file_field.path)
    except Exception:
        return False