from decimal import Decimal
from uuid import uuid4
import sys

import allure
import pytest

from common.report import capture_failure_safely, checkpoint, current_report, step
from common.test_case import TestCase
from page.page_objects.order_po import money


class OrderCase(TestCase):
    __test__ = False
    order_type = None

    def init(self):
        self.orders = None
        self.save_attempted = False
        self.saved = False
        self.note = "uitest-" + uuid4().hex
        self.account = self.database.account("admin")
        self.data = self.database.get("orders", self.order_type)
        self.expected_total = sum(Decimal(i["price"]) * i["quantity"] for i in self.data["items"])
        self.title = "添加销售订单（多行商品）" if self.order_type == "sale" else "添加采购订单"

    def setup(self):
        step("预置步骤：登录 ERP")
        self.aw.login_as(self.account)

    def process(self):
        step("步骤1：打开订单管理")
        self.orders = self.aw.open_orders(self.order_type)

        step("步骤2：新建订单并填写商品明细")
        self.orders.new_order().fill_order(self.data, self.note)

        checkpoint("检查点1：草稿金额按数量和单价计算")
        self.checks.equal(self.orders.form_total(), money(self.expected_total), "表单合计")

        step("步骤3：保存订单草稿")
        self.save_attempted = True  # 提交成功但等待失败时，teardown 仍按唯一备注查找。
        self.orders.save()
        self.saved = True

        step("步骤4：查询本次订单并打开详情")
        self.orders.open_created(self.note)
        details = self.orders.details()

        checkpoint("检查点2：订单字段、状态和金额正确")
        self.checks.equal(details["status"], "草稿", "订单状态")
        self.checks.equal(details["total"], "合计 " + money(self.expected_total), "订单金额")
        self.checks.equal(details["note"], "备注：" + self.note, "订单备注")
        self.checks.equal(details["number"].startswith("SO-" if self.order_type == "sale" else "PO-"), True, "单据编号前缀")
        self.checks.equal(self.data["partner"] in details["parties"], True, "往来单位")
        self.checks.equal(self.data["warehouse"] in details["parties"], True, "仓库")
        self.checks.equal(len(details["items"]), len(self.data["items"]), "商品行数")
        for actual, expected in zip(details["items"], self.data["items"]):
            self.checks.equal(actual[0].splitlines()[-1], expected["product_code"], "商品编码")
            self.checks.equal(actual[1].split()[0], str(expected["quantity"]), "商品数量")
            self.checks.equal(actual[2], money(expected["price"]), "商品单价")
            self.checks.equal(actual[3], money(Decimal(expected["price"]) * expected["quantity"]), "商品小计")

        step("步骤5：刷新页面后重新查询订单")
        self.context.driver.refresh()
        self.orders.open_created(self.note)

        checkpoint("检查点3：订单已持久化")
        self.checks.equal(self.orders.details()["number"], details["number"], "持久化订单编号")

    def teardown(self):
        errors = []
        try:
            if getattr(self, "save_attempted", False) and self.orders:
                step("恢复步骤1：取消本次测试创建的草稿")
                found = self.orders.cancel_created(self.note)
                if self.saved and not found:
                    raise AssertionError("已保存的测试订单未找到，无法确认恢复完成")
        except Exception as error:
            capture_failure_safely(self.context, "取消订单")
            current_report().finish(sys.exc_info())
            errors.append(error)
        try:
            step("恢复步骤2：退出当前测试会话")
            self.aw.logout_if_logged_in()
        except Exception as error:
            capture_failure_safely(self.context, "退出登录")
            current_report().finish(sys.exc_info())
            errors.append(error)
        if errors:
            raise ExceptionGroup("测试环境恢复失败", errors)


@pytest.mark.ui
@pytest.mark.smoke
@allure.feature("订单")
class TestAddSaleOrder(OrderCase):
    __test__ = True
    order_type = "sale"


@pytest.mark.ui
@pytest.mark.smoke
@allure.feature("订单")
class TestAddPurchaseOrder(OrderCase):
    __test__ = True
    order_type = "purchase"
