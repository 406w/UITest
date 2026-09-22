from decimal import Decimal
from urllib.parse import urlencode

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from common.elements import AmbiguousElement
from page.page_elements.order_page import OrderPage
from page.page_objects.home_po import BasePO


def money(value):
    return f"¥{Decimal(str(value)):,.2f}"


class OrderPO(BasePO):
    elements = OrderPage
    order_type = None

    def wait_ready(self):
        expected = "销售管理" if self.order_type == "sale" else "采购管理"
        self.ops.wait(lambda d: self.element(OrderPage.heading).text() == expected and
                      not d.find_elements(By.CSS_SELECTOR, "#content .loading"), "订单列表未加载")
        return self

    def open(self, query=""):
        self.driver.get(self.context.config.base_url.rstrip("/") + f"/#/{self.order_type}?" + urlencode({"q": query}))
        self.wait_ready()
        # 等待本次请求渲染出的筛选值，避免读取旧列表。
        self.ops.wait(lambda d: d.find_element(By.CSS_SELECTOR, '#filter-form [name="q"]').get_attribute("value") == query,
                      "订单筛选结果未更新")
        return self

    def new_order(self):
        self.element(OrderPage.new).click()
        self.ops.find(lambda d: self.resolve(d, OrderPage.form))
        return self

    def fill_order(self, data, note):
        self.element(OrderPage.partner).select(text=data["partner"])
        self.element(OrderPage.warehouse).select(text=data["warehouse"])
        for index, item in enumerate(data["items"]):
            if index:
                self.element(OrderPage.add_line).click()
            prefix = f'#order-lines [data-line="{index}"]'
            control = Select(self.driver.find_element(By.CSS_SELECTOR, prefix + ' select[name="product_id"]'))
            matches = [o for o in control.options if o.text.startswith(item["product_code"] + " · ")]
            if len(matches) != 1:
                raise AmbiguousElement(f"商品编码 {item['product_code']} 匹配 {len(matches)} 项")
            control.select_by_value(matches[0].get_attribute("value"))
            # 商品选择后前端会重建行，每次重新解析元素。
            for name in ("quantity", "price"):
                declaration = type(f"line_{index}_{name}", (), {
                    "__doc__": f"第 {index + 1} 行 {name}", "css": prefix + f' input[name="{name}"]'})
                self.element(declaration).fill(item[name])
        self.element(OrderPage.note).fill(note)
        return self

    def form_total(self):
        return self.element(OrderPage.total).text()

    def save(self):
        self.element(OrderPage.save).click()
        self.ops.wait(lambda d: not d.find_elements(By.CSS_SELECTOR, "#modal[open]"), "订单保存失败，弹窗未关闭")
        return self.wait_ready()

    def close_modal(self):
        if self.driver.find_elements(By.CSS_SELECTOR, "#modal[open]"):
            declaration = type("close", (), {"css": '#modal[open] [aria-label="关闭弹窗"]'})
            self.element(declaration).click()
            self.ops.wait(lambda d: not d.find_elements(By.CSS_SELECTOR, "#modal[open]"), "弹窗未关闭")

    def matching_links(self):
        return self.driver.find_elements(By.CSS_SELECTOR, '#content tbody a[data-action="order-detail"]')

    def open_created(self, note, required=True):
        self.close_modal()
        self.open(note)
        if required:
            self.ops.wait(lambda d: self.matching_links(), "未找到刚创建的订单")
        links = self.matching_links()
        if not links:
            return None
        if len(links) != 1:
            raise AmbiguousElement(f"测试备注匹配 {len(links)} 个订单，拒绝继续")
        order_id = links[0].get_attribute("data-id")
        links[0].click()
        self.ops.find(lambda d: self.resolve(d, OrderPage.detail_number))
        if self.element(OrderPage.detail_note).text() != "备注：" + note:
            raise AssertionError("订单备注不完全匹配，拒绝操作非本用例订单")
        return order_id

    def details(self):
        rows = self.driver.find_elements(By.CSS_SELECTOR, "#modal[open] tbody tr")
        return {
            "number": self.element(OrderPage.detail_number).text(),
            "status": self.element(OrderPage.detail_status).text(),
            "total": self.element(OrderPage.detail_total).text(),
            "note": self.element(OrderPage.detail_note).text(),
            "items": [[cell.text for cell in row.find_elements(By.CSS_SELECTOR, "td")] for row in rows],
            "parties": self.driver.find_element(By.CSS_SELECTOR, "#modal[open] .details").text,
        }

    def cancel_created(self, note):
        if not note.startswith("uitest-"):
            raise ValueError("仅允许恢复带 uitest- 唯一标记的本次测试订单")
        if self.open_created(note, required=False) is None:
            return False
        state = self.element(OrderPage.detail_status).text()
        if state == "已取消":
            self.close_modal()
            return True
        if state != "草稿":
            raise AssertionError(f"仅取消本测试草稿，实际状态：{state}")
        self.element(OrderPage.cancel).click()
        self.element(OrderPage.confirm_cancel).click()
        self.ops.wait(lambda d: not d.find_elements(By.CSS_SELECTOR, "#modal[open]"), "取消订单失败")
        self.open_created(note)
        if self.element(OrderPage.detail_status).text() != "已取消":
            raise AssertionError("订单恢复未成功")
        self.close_modal()
        return True


class SalePO(OrderPO):
    page_key = "sale"
    order_type = "sale"


class PurchasePO(OrderPO):
    page_key = "purchase"
    order_type = "purchase"
