from django import template
import logging

register = template.Library()
logger = logging.getLogger(__name__)

@register.filter(name='get_item')
def get_item(dictionary, key):
    logger.debug(f"Attempting to get item with key: {key}")
    logger.debug(f"Dictionary: {dictionary}")
    value = dictionary.get(key)
    logger.debug(f"Retrieved value: {value}")
    return value

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)