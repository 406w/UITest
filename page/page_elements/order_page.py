class OrderPage:
    class heading:
        """订单列表标题"""
        css = "#content h1"

    class new:
        """新建订单"""
        attrs = {"data-action": "new-order"}

    class form:
        """订单编辑表单"""
        id = "order-form"

    class partner:
        """客户或供应商"""
        css = '#order-form select[name="partner_id"]'

    class warehouse:
        """订单仓库"""
        css = '#order-form select[name="warehouse_id"]'

    class note:
        """订单备注"""
        css = '#order-form textarea[name="note"]'

    class add_line:
        """添加商品行"""
        attrs = {"data-action": "add-line"}

    class save:
        """保存订单草稿"""
        css = '#order-form [data-testid="form-submit"]'

    class total:
        """草稿合计金额"""
        id = "order-total"

    class detail_number:
        """详情中的单据编号"""
        css = "#modal[open] h3.mono"

    class detail_status:
        """详情中的单据状态"""
        css = "#modal[open] .row.spread > .badge"

    class detail_total:
        """详情中的合计金额"""
        css = "#modal[open] .total"

    class detail_note:
        """详情中的备注"""
        css = "#modal[open] .detail-note"

    class cancel:
        """取消本次创建的订单"""
        css = '#modal[open] [data-command="cancel"]'

    class confirm_cancel:
        """确认取消订单"""
        css = '#action-form[data-command="cancel"] [data-testid="form-submit"]'
