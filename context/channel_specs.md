# Channel specs and accessibility rules

These are checked **by code, not by a model**: a limit is either met or it isn't. The machine-readable copy is `channel_specs.json`; keep both in sync.

## Google Search: Responsive Search Ad (RSA)
Source: Google Ads Help, "About responsive search ads"

| ID | Field | Rule |
|---|---|---|
| CH-RSA-01 | Headlines | 3 to 15 headlines, each max **30** characters |
| CH-RSA-02 | Descriptions | 2 to 4 descriptions, each max **90** characters (aim for 60+, see CH-MIN) |
| CH-RSA-03 | Display path | Up to 2 path fields, each max **15** characters |
| CH-RSA-04 | Headline uniqueness | No duplicate headlines |

## Google Display: Responsive Display Ad (RDA)
Source: Google Ads Help, "About responsive display ads"

| ID | Field | Rule |
|---|---|---|
| CH-RDA-01 | Short headline | Max **30** characters |
| CH-RDA-02 | Long headline | Max **90** characters (aim for 45+, see CH-MIN) |
| CH-RDA-03 | Description | Max **90** characters (aim for 50+, see CH-MIN) |
| CH-RDA-04 | Business name | Max **25** characters |
| CH-RDA-05 | Landscape image | 1.91:1 ratio; recommended 1200×628, minimum 600×314 |
| CH-RDA-06 | Square image | 1:1 ratio; recommended 1200×1200, minimum 300×300 |
| CH-RDA-07 | Image file size | Max 5,120 KB |
| CH-RDA-08 | Image text | Text overlay should cover no more than 20% of the image (Northwind house rule) |

## Launch email
Northwind house rules, based on common email practice. Not a platform limit.

| ID | Field | Rule |
|---|---|---|
| CH-EM-01 | Subject line | Max **50** characters |
| CH-EM-02 | Preheader | Max **100** characters (aim for 40+, see CH-MIN) |
| CH-EM-03 | Hero image | 1200×600 (displays at 600 px wide) |
| CH-EM-04 | Body copy | Max 120 words |
| CH-EM-05 | Required elements | CTA button, physical postal address, unsubscribe link (see REG-08) |

## Minimum lengths (CH-MIN)
Northwind house standard, not a platform limit. Paid placements with lots of room should use it. Copy below the minimum gets a **warning** (approvable with a note), never a block.

| Field | Aim for |
|---|---|
| RSA description | 60 to 90 characters |
| RDA long headline | 45 to 90 characters |
| RDA description | 50 to 90 characters |
| Email preheader | 40 to 100 characters |

No minimum on RSA headlines, short headlines, subject lines, business name or alt text: short is often right there.

## Accessibility (all channels)
Source: WCAG 2.2

| ID | Rule |
|---|---|
| ACC-01 | Every image has alt text, 125 characters max, describing what the image shows (WCAG 1.1.1) |
| ACC-02 | Text over images or color backgrounds has contrast of at least 4.5:1 (WCAG 1.4.3) |
| ACC-03 | CTA link text says what it does ("Shop the Cascade Shell"), never "Click here" (WCAG 2.4.4) |
| ACC-04 | No meaning carried by color alone (WCAG 1.4.1) |
