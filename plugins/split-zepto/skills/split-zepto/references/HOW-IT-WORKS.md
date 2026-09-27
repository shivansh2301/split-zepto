# How the split works

Every item you buy on Zepto goes through four steps: **Category → Pool → Participation → Deny**. Whoever is left at the end shares the cost equally.

```
 item bought ──► CATEGORY ──► POOL ──► PARTICIPATION ──► DENY ──► split equally
 "Onion 1 kg"     vegetables    Kitchen    who was home?     anyone said     among whoever
                                           (that day)        "not me"?       is left
```

## 1. Category: *what is it?*
The skill reads the item name and gives it a category: vegetables, pantry (rice, atta, dal, oil), dairy, meat, cleaning, sweets, and so on. You never type categories. They come from a built-in list that improves over time.

If an item matches no category, it's **yours**. It isn't asked about or named, and nobody else pays for it.

## 2. Pool: *which shared pot does it come out of?*
A pool is a group expense your flat agreed to share. Most flats need just two:

| Pool | Typical categories |
|---|---|
| **Kitchen** | vegetables, fruit, pantry, dairy, eggs, bread, spices, meat |
| **House** | cleaning, detergent, home items |
| *(no pool)* | sweets, snacks, cold drinks, personal care → **the buyer pays** |

Each category points to one pool, or to none.

## 3. Participation: *who's in the pool for this purchase?*
Everyone who lives in the flat is in both pools, **as long as they were home** on the day of the order.

- **Default: only whoever was home pays.** If you were away for a week, you don't pay for that week's vegetables, milk or detergent.
- **Exception: long-lasting staples.** For rice, atta, dal, oil, ghee and spices, everyone pays, even if away. You'll use them when you're back.
- **Not moved in yet or already moved out** counts as "not home" for those dates.

## 4. Deny: *anyone who says "not me"?*
Anyone can **deny** a whole category or a single item. Denying takes them out of the split for it, even though they're in the pool.

- **Category deny:** "I don't eat meat" removes you from every meat purchase.
- **Pool deny:** "I only share house things, not kitchen" removes you from the whole Kitchen pool.
- **Item deny by the buyer:** "Tortillas are only mine" means nobody else is charged for tortillas you buy. Everyone else effectively denies them.
- **One-off:** "Just this order is mine" applies to that one purchase only.

**Deny always wins**, over the pool and over participation.

---

## Worked examples (an example flat: ME, AK, PS, RJ)

**Setup:**
- **Kitchen:** ME, AK, PS. RJ denies the Kitchen pool.
- **House:** all four.
- **PS** denies meat.
- **PS** was away 5–25 Jun.
- **RJ** moved in on 1 Apr.

| Purchase | Category → Pool | Participation (home that day) | Deny | Split |
|---|---|---|---|---|
| Mushrooms, 3 Sep | vegetables → Kitchen | ME, AK, PS | none | ÷3 |
| Chicken, 3 Sep | meat → Kitchen | ME, AK, PS | PS denies meat | ME + AK ÷2 |
| Diet Coke, 12 Jun | Diet Coke → Kitchen | ME, AK (PS away) | none | ME + AK ÷2 |
| Ghee, 15 Jun | pantry → Kitchen, *even if away* | ME, AK, PS (PS away, but pantry counts everyone) | none | ÷3 |
| Detergent, 19 May | cleaning → House | all four | none | ÷4 |
| Kitchen roll, 20 Mar | home → House | ME, AK, PS (RJ not moved in) | none | ÷3 |
| Tortillas, 24 May | pantry → Kitchen | ME, AK, PS | ME: "only mine" | ME pays |
| Chocolate, any day | sweets → no pool | n/a | n/a | buyer pays |

---

## What stays private
- **What gets shared:** only the Kitchen and House items go into the file you share. Your own items never leave your machine.
- **Unmatched items** are never named. They default to you.
- **"Only mine" decisions** are saved as unreadable codes. You can see them yourself with `/split-zepto prefs --reveal`.
- **People are initials** (AK, PS). No names, addresses or phone numbers are stored. The only location kept is the delivery pincode, used to flag orders sent somewhere else.
- **The only model-visible data:** fetching orders means the AI sees the order details, since that's how the Zepto connection works. It never repeats or stores them beyond the above.

## How you control it
- **First run:** pick a starting preset (most flats keep the default), then answer a few click questions about what you actually buy.
- **After each run:** a few questions about new or unusual items. Answer, see how everyone's total changes, then choose "save" or "just this time".
- **Any time:**
  - **`/split-zepto prefs`:** see your pools, who's in them, away dates, denies and saved decisions in plain words.
  - **`/split-zepto change`:** change any of them, with the same click questions.
