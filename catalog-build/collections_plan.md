# Automated collections (Shopify: Products > Collections > Automated)

Every one of these is self-maintaining: new designs join automatically.

## Garment collections — one per style

| Collection | Handle | Condition | Products |
|---|---|---|---|
| Hoodie | `hoodie` | Product type **is equal to** `Hoodie` | 54 |
| Oversized Heavy Premium | `oversized-heavy-premium` | Product type **is equal to** `Oversized Heavy Premium` | 61 |
| Oversized Light-Soft | `oversized-light-soft` | Product type **is equal to** `Oversized Light-Soft` | 61 |
| Regular Fit T-Shirt | `regular-fit-t-shirt` | Product type **is equal to** `Regular Fit T-Shirt` | 45 |
| Sweatshirt | `sweatshirt` | Product type **is equal to** `Sweatshirt` | 54 |

## Season collections — these are what you discount

| Collection | Handle | Condition | Products |
|---|---|---|---|
| Winter Collection | `winter-collection` | Product type = `Hoodie` OR Product type = `Sweatshirt` (match **any**) | 108 |
| Summer Collection | `summer-collection` | Product type = `Oversized Heavy Premium` OR Product type = `Oversized Light-Soft` OR Product type = `Regular Fit T-Shirt` (match **any**) | 167 |

> Set the condition matcher to **any** for season collections, **all** for garment collections.

## Winter sale, the native way

1. Discounts > Create discount > **Amount off products** > Automatic
2. Applies to: **Specific collections** > `Winter Collection`
3. Value: e.g. 25% off. Set start/end dates. Save.

That is the whole job. It covers every hoodie and sweatshirt across every design, including designs you add next week, and it touches no t-shirt.
