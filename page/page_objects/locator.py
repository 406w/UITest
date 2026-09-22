from dataclasses import dataclass
from functools import wraps


@dataclass(frozen=True)
class Route:
    source: str
    element_key: str
    target: str
    action: str


PAGE_TYPES = {}
ROUTES = {}


def jump(source, element_key, target):
    def decorate(action):
        key = source, action.__name__
        if key in ROUTES:
            raise ValueError(f"重复跳转声明：{key}")
        ROUTES[key] = Route(source, element_key, target, action.__name__)

        @wraps(action)
        def wrapped(self, *args, **kwargs):
            if self.page_key != source:
                raise ValueError("跳转源页面不匹配")
            target_type = PAGE_TYPES[target]
            action(self, *args, **kwargs)
            return target_type(self.context).wait_ready()
        return wrapped
    return decorate


def initialize_page_registry():
    from page.page_objects.home_po import HomePO
    from page.page_objects.login_po import LoginPO
    from page.page_objects.order_po import PurchasePO, SalePO
    PAGE_TYPES.update({p.page_key: p for p in (HomePO, LoginPO, PurchasePO, SalePO)})
    for route in ROUTES.values():
        if route.source not in PAGE_TYPES or route.target not in PAGE_TYPES:
            raise ValueError(f"未知跳转页面：{route}")
        if not hasattr(PAGE_TYPES[route.source].elements, route.element_key):
            raise ValueError(f"未知跳转元素：{route}")


def ways_to(target, source=None):
    initialize_page_registry()
    return [route for route in ROUTES.values()
            if route.target == target and (source is None or route.source == source)]
