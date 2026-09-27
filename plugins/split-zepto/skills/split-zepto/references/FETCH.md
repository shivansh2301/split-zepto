# Fetching Zepto orders

## 1. Page through the history
Call `list_order_history(limit=50, pageNumber=1, 2, …)`. Zepto returns **8 orders per page** whatever the limit.

Each order `id` is a UUIDv7. Its first 12 hex digits are the order time in milliseconds since epoch:

```python
from datetime import datetime, timezone
ms = int(order_id.replace("-", "")[:12], 16)
datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
```

**Stop paging** once the last order on a page is older than the period start. Don't fetch details for anything outside the period.

## 2. Get details for DELIVERED orders only
Call `get_order_detail(orderId)` for each delivered order in the period. Several calls in parallel are fine.

**Cancelled orders don't need a detail call.** Record them from the list data with no prices:
```json
{"id":"…","code":"…","placed":null,"status":"CANCELLED","item_total":null,"fees":0,"order_discount":0,"grand_total":<list grandTotalAmount>,"refund":0,"pincode":null,"items":[["<name>","",<count>,null,null,0]]}
```

## 3. Write one normalized line per order
```json
{"id":"<id>","code":"<code>","placed":"<placedTime, trimmed to seconds, with Z>","status":"DELIVERED",
 "item_total":<sum of line totals>,"fees":<billSummary.totalBill - sum of line totals, if > 0, else 0>,
 "order_discount":0,"grand_total":<grandTotalAmount>,"refund":<totalRefundAmount>,
 "pincode":"<6 digits from the address, or null if it's masked (***) or missing>",
 "items":[["<productName>","<brand>",<quantityFulfilled>,<unit = line/qty>,<totalFinalSellingPrice>,<item totalRefundAmount>]]}
```
- **Amounts** are in **paise**, exactly as Zepto returns them. Don't convert them.
- **Items** come from **every shipment** in `shipments[].products[]`.
- **Line totals:** use `totalFinalSellingPrice` as the line total, including 0 for free promo items.
- **Addresses:** from `userAddressFormatted`, take **only the 6-digit pincode**. Never copy, repeat or summarize the rest.
- **Leave out:** invoice URLs, image paths, shipment IDs and delivery times.

The build step checks that each delivered order's lines + fees − discount = total − refund, and prints any mismatch.
