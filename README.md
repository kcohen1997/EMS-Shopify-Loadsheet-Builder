# Eddie Motorsports Shopify Product Loadshet

This repository creates a GUI cleaning up Eddie Motorsports product information from the e-commerce site Shopify. The resulting Loadsheet contains the following information:

* **Handle**: a user and URL-friendly version of a product (taken from the "Handle" field)
* **Title**: title of product (taken from "Title" field)
* **Part #**: identification (id) for product/variant (taken from "Variant SKU" field)
* **Full Title**: title of product, including the specific variant if there is one (taken from "Title", "Option1 Value", "Option2 Value" and "Option3 Value" field)
* **Category**: category of product (taken from "Product Category" field)
* **Retail Price**: retail price of product/variant (taken from "Variant Price" field)
* **Jobber Price**: jobber price of product/variant, (calculated from "Variant Price" field, default is 0.85 times the Retail Price)
* **Dealer Price**: dealer price of product/variant, (calculated from "Variant Price" field, default is 0.75 times the Retail Price)
* **OEM/WD Price**: oem/wd price of product/variant, (calculated from "Variant Price" field, default is 0.675 times the Retail Price)
* **Length (in)**: length of product (taken from "length" metafield)
* **Width (in)**: width of product (taken from "width" metafield)
* **Height (in)**: height of product (taken from "height" metafield)
* **Weight (lb)**: weight of product converted from grams to lbs (taken from "Product Grams" field)
* **Description**: description of product (taken from "Body (HTML)" field)
* **Image 1**: image url of product (taken from "Image Src" field)

To access the completed exe file, visit the "Release" section.

## How To Create Executable File

### Step 1: Download Product CSV File from Shopify and Python File From Repository (create_shopify_loadsheet.py)

If using sample csv file, download "shopify_sample_data.csv"

### Step 2: Download the following onto your computer:

#### Python (Programming Language): 

How To Download:

https://www.python.org/downloads/

Run this command in the terminal to see if downloaded properly:

```bash
python --version
```

pyinstaller --onefile --noconsole create_shopify_loadsheet.py

#### Pip (Python Package Manager):

How To Download:

pip install pyinstaller

Run this command in the terminal to see if downloaded properly:

```bash
pip --version
```

#### Pyinstaller (Converts Python Scripts Into Executable Files):

How To Download:

pip download pyinstaller

Run this command in the terminal to see if downloaded properly:

```bash
pyinstaller --version
```
### Step 3:  In terminal, go to the same folder/directory as the Python file and enter the following command:

```bash
pyinstaller --onefile --noconsole create_shopify_loadsheet.py
```
