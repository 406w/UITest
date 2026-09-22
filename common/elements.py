"""把嵌套 PE 类转为 AND 条件，不在 PE 保存 WebElement。"""
import inspect
import re

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By


class AmbiguousElement(RuntimeError):
    pass


class MissingResolver(ValueError):
    pass


def description(declaration):
    return inspect.getdoc(declaration) or declaration.__qualname__


def xpath_literal(value):
    value = str(value)
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    return "concat(" + ", \"'\", ".join(f"'{p}'" for p in value.split("'")) + ")"


def parse_declaration(declaration):
    fields = {}
    for parent in reversed(declaration.__mro__):
        fields.update({k: v for k, v in vars(parent).items() if not k.startswith("_")})
    unknown = fields.keys() - {"id", "name", "type", "tag", "text", "css", "xpath", "attrs", "meta"}
    if unknown:
        raise ValueError(f"未注册的元素字段：{sorted(unknown)}")
    if "css" in fields and "xpath" in fields:
        raise ValueError("css 与 xpath 不能同时声明")
    attrs = dict(fields.get("attrs", {}))
    for key in ("id", "name", "type"):
        if key in fields:
            if key in attrs and str(attrs[key]) != str(fields[key]):
                raise ValueError(f"重复属性冲突：{key}")
            attrs[key] = str(fields[key])
    for key in attrs:
        if not re.fullmatch(r"[A-Za-z_][\w:.-]*", key):
            raise ValueError(f"非法 HTML 属性名：{key}")
    fields["attrs"] = {k: str(v) for k, v in attrs.items()}
    if not attrs and not any(k in fields for k in ("tag", "text", "css", "xpath")):
        raise MissingResolver(declaration.__qualname__)
    return fields


def resolve_declared_element(root, declaration):
    fields = parse_declaration(declaration)
    attrs = fields["attrs"]
    if "css" in fields:
        by, value = By.CSS_SELECTOR, fields["css"]
    elif "xpath" in fields:
        by, value = By.XPATH, fields["xpath"]
    else:
        conditions = [f"@{key}={xpath_literal(value)}" for key, value in attrs.items()]
        if "tag" in fields:
            conditions.append(f"local-name()={xpath_literal(fields['tag'])}")
        # 文本在最终过滤时检查可见文本；属性尽早收窄范围。
        value = ".//*" + ("[" + " and ".join(conditions) + "]" if conditions else "")
        by = By.XPATH
    elements = root.find_elements(by, value)
    matches = []
    for element in elements:
        if any(element.get_dom_attribute(k) != v for k, v in attrs.items()):
            continue
        if "tag" in fields and element.tag_name != fields["tag"]:
            continue
        if "text" in fields and element.text.strip() != fields["text"]:
            continue
        matches.append(element)
    if not matches:
        raise NoSuchElementException(description(declaration))
    if len(matches) > 1:
        raise AmbiguousElement(f"{declaration.__qualname__} 匹配 {len(matches)} 个元素")
    return matches[0]
