import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
import chardet
import threading
import re

# --- Float Validation ---
def validate_float_input(new_value):
    if new_value == "":
        return True
    try:
        float(new_value)
        return True
    except ValueError:
        return False

# --- Text Placeholder Function ---
def add_placeholder(entry, text):
    entry.insert(0, text)
    entry.config(fg="gray")

    def on_focus_in(event):
        if entry.get() == text:
            entry.delete(0, tk.END)
            entry.config(fg="black")

    def on_focus_out(event):
        if entry.get() == "":
            entry.insert(0, text)
            entry.config(fg="gray")

    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)

# --- Helper: Extract common SKU prefix per handle ---
def get_common_variant_sku_prefix(group):
    skus = group['Variant SKU'].dropna().astype(str).unique()
    if len(skus) == 0:
        return ""
    prefix = skus[0]
    for sku in skus[1:]:
        i = 0
        while i < len(prefix) and i < len(sku) and prefix[i] == sku[i]:
            i += 1
        prefix = prefix[:i]
        if prefix == "":
            break
    return prefix


def common_prefix(strings):
    strings = [str(s) for s in strings if pd.notna(s)]
    if not strings:
        return ''
    prefix = strings[0]
    for s in strings[1:]:
        s = str(s)
        i = 0
        while i < len(prefix) and i < len(s) and prefix[i] == s[i]:
            i += 1
        prefix = prefix[:i]
        if prefix == '':
            break
    # Remove trailing dash if present
    if prefix.endswith('-'):
        prefix = prefix[:-1].rstrip()  # Also remove any trailing spaces after dash removal
    return prefix

def group_key(row):
    handle = str(row.get('Handle') or '').strip()
    option1 = str(row.get('Option1 Value') or '').strip()
    option2 = str(row.get('Option2 Value') or '').strip()
    option3 = str(row.get('Option3 Value') or '').strip()

    if option3:
        return (handle, option1, option2)  # Group by Handle + Option1 if Option2 exists
    else:
        if option2:
            return (handle, option1)  # Group by Handle + Option1 if Option2 exists
        else:
            return (handle,)          # Group only by Handle if no Option2
    
# --- Background Processing Function ---
def _process_file_worker(file_path):
    try:
        # Step 1: Detect file encoding by reading raw bytes and using chardet
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            encoding = chardet.detect(raw_data)['encoding']

        # Step 2: Read CSV file into a DataFrame using detected encoding
        df = pd.read_csv(file_path, encoding=encoding)

        # Step 3: Define required columns and check if any are missing
        required_columns = [
            'Handle', 'Variant SKU', 'Title', 'Variant Price', 'Body (HTML)', 'Option1 Value',
            'Option2 Value', 'Option3 Value', 'Published', 'Status', 'Variant Grams', 'Image Src'
        ]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

        # Step 4: Configure pandas option to avoid silent downcasting issues (future-proofing)
        pd.set_option('future.no_silent_downcasting', True)

        # Step 5: Forward fill missing values in 'Title', 'Published', and 'Status' columns
        df['Title'] = df['Title'].ffill()
        df['Published'] = df['Published'].infer_objects().ffill()
        df['Status'] = df['Status'].ffill()

        # Step 6: Clean and prepare string columns for consistency (strip whitespace)
        df['Title'] = df['Title'].fillna('').astype(str).str.strip()

        # Step 7: Convert 'Variant Price' to numeric, coercing errors to NaN
        df['Variant Price'] = pd.to_numeric(df['Variant Price'], errors='coerce')

        # Step 8: Fill missing option values with empty strings and strip whitespace
        df['Option1 Value'] = df['Option1 Value'].fillna('').astype(str).str.strip()
        df['Option2 Value'] = df['Option2 Value'].fillna('').astype(str).str.strip()
        df['Option3 Value'] = df['Option3 Value'].fillna('').astype(str).str.strip()

        # Step 9: Filter DataFrame to keep only rows where:
        # - Variant Price > 0
        # - Published is 'true' (case insensitive)
        # - Status is 'active' (case insensitive)
        df = df[
            (df['Variant Price'] > 0) &
            (df['Published'].astype(str).str.lower() == 'true') &
            (df['Status'].astype(str).str.lower() == 'active')
        ]

        # Step 10: Raise error if any 'Variant Price' values are still invalid (NaN)
        if df['Variant Price'].isna().sum() > 0:
            raise ValueError("Some rows have invalid or missing 'Variant Price' values.")

        # Step 11: Create 'Option Suffix' by concatenating non-empty Option values with ' - ' separator
        df['Option Suffix'] = df[['Option1 Value', 'Option2 Value', 'Option3 Value']].apply(
            lambda row: ' - '.join([val for val in row if val]), axis=1
        )

        # Step 12: Append 'Option Suffix' to 'Title' (if suffix exists)
        df['Title'] = df.apply(
            lambda row: f"{row['Title']} - {row['Option Suffix']}" if row['Option Suffix'] else row['Title'],
            axis=1
        )

        # Step 13: Remove the string '- Default Title' from the 'Title' column
        df['Title'] = df['Title'].astype(str).str.replace('- Default Title', '', regex=False)

        # Step 14: Calculate weight in pounds from grams, rounding to 2 decimals
        df['Weight (lb)'] = round(df['Variant Grams'] * 0.00220462, 2)

        # Step 15: Attempt to read multiplier values from user input (GUI entries)
        # If invalid input, show error message and re-enable buttons, then exit
        try:
            jobber_multiplier = float(jobber_price_entry.get()) if jobber_price_entry.get() else 0.85
            dealer_multiplier = float(dealer_price_entry.get()) if dealer_price_entry.get() else 0.75
            oemwd_multiplier = float(oemwd_price_entry.get()) if oemwd_price_entry.get() else 0.675
        except ValueError:
            root.after(0, lambda: [
                status_label.config(text="Error: Invalid multiplier"),
                messagebox.showerror("Input Error", "Please enter valid numeric values for multipliers."),
                process_button.config(state=tk.NORMAL)
            ])
            return

        # Step 16: Conditionally calculate and add price columns based on checkboxes
        if jobber_price_var.get():
            df['Jobber Price'] = round(df['Variant Price'] * jobber_multiplier, 2)
        if dealer_price_var.get():
            df['Dealer Price'] = round(df['Variant Price'] * dealer_multiplier, 2)
        if oemwd_price_var.get():
            df['OEM/WD Price'] = round(df['Variant Price'] * oemwd_multiplier, 2)

        # Step 17: If including product metafields, forward fill those columns if any non-empty exist
        product_metafield_columns = []
        if include_product_metafields_var.get():
            product_metafield_columns = [
                col for col in df.columns if "metafields" in col and not df[col].isna().all()
            ]
            df[product_metafield_columns] = df[product_metafield_columns].ffill()

        # Step 18: Remove rows where 'Variant SKU' is missing or empty
        df = df[df['Variant SKU'].notna() & (df['Variant SKU'].astype(str).str.strip() != '')]

        # Step 19: Create a grouping key for grouping related variants (custom function)
        df['group_key'] = df.apply(group_key, axis=1)

        # Step 20: Group DataFrame by 'group_key'
        grouped = df.groupby('group_key')

        # Step 21: Calculate the common prefix of 'Variant SKU's within each group (custom function)
        common_prefixes = grouped['Variant SKU'].apply(lambda parts: common_prefix(parts.tolist()))

        # Step 22: Map the common prefixes back to each row using the group key
        df['Parent #'] = df['group_key'].map(common_prefixes)

        # Step 23: For any common prefix without a dash '-', replace with that row's own 'Variant SKU'
        df['Parent #'] = df.apply(
            lambda row: row['Variant SKU'] if '-' not in str(row['Parent #']) else row['Parent #'],
            axis=1
        )

        # Step 24: (Optional, but redundant here) Re-map common prefixes again after previous replacement
        df['Parent #'] = df['group_key'].map(common_prefixes)

        # Step 25: Prepare list of price columns that were added, based on user input
        price_cols = []
        if jobber_price_var.get():
            price_cols.append('Jobber Price')
        if dealer_price_var.get():
            price_cols.append('Dealer Price')
        if oemwd_price_var.get():
            price_cols.append('OEM/WD Price')

        # Step 26: Define the final set of columns for output DataFrame
        final_columns = (
             ['Variant SKU', 'Parent #', 'Title', 'Variant Price'] +
             price_cols + ['Body (HTML)', 'Weight (lb)', 'Image Src'] +
             product_metafield_columns
        )
        
        # Step 27: Create a new DataFrame with only the final selected columns
        final_variant_list = df[final_columns].copy()

        # Step 28: Clean metafield column names by removing trailing "(product.metafields...)" patterns
        cleaned_column_names = {
            col: re.sub(r"\s*\(product\.metafields.*?\)", "", col).strip()
            for col in product_metafield_columns
        }
        final_variant_list.rename(columns=cleaned_column_names, inplace=True)

        # Step 29: Rename some columns to user-friendly or standard output names
        final_variant_list.rename(columns={
            'Variant SKU': 'Part #',
            'Variant Price': 'Retail Price',
            'Body (HTML)': 'Description',
            'Image Src': 'Image',
            'Common SKU Prefix': 'Common Part Prefix'
        }, inplace=True)

        # Step 30: Clean 'Fitment' column by replacing '|' with space and newlines with comma + space
        if 'Fitment' in final_variant_list.columns:
            final_variant_list['Fitment'] = final_variant_list['Fitment'].astype(str).str.replace('|', ' ', regex=False).str.replace('\n', ', ', regex=False)

        # Step 31: Save the processed data globally for further use (e.g., saving/exporting)
        global processed_data
        processed_data = final_variant_list

        # Step 32: Notify UI of success, re-enable buttons, update status label, and show message box
        root.after(0, lambda: [
            save_button.config(state=tk.NORMAL),
            process_button.config(state=tk.NORMAL),
            status_label.config(text="Done"),
            messagebox.showinfo("Success", "File processed successfully!")
        ])

    except Exception as e:
        # Step 33: Handle any errors, update UI accordingly, re-enable buttons, and show error message
        root.after(0, lambda error=e: [
            status_label.config(text="Error during processing"),
            process_button.config(state=tk.NORMAL),
            messagebox.showerror("Error", str(error))
        ])


# --- Main Process Trigger ---
def process_file():
    process_button.config(state=tk.DISABLED)
    save_button.config(state=tk.DISABLED)
    status_label.config(text="Processing...")

    try:
        jobber_multiplier = float(jobber_price_entry.get()) if jobber_price_entry.get() else 0.85
        dealer_multiplier = float(dealer_price_entry.get()) if dealer_price_entry.get() else 0.75
        oemwd_multiplier = float(oemwd_price_entry.get()) if oemwd_price_entry.get() else 0.675
        for name, value in [('Jobber', jobber_multiplier), ('Dealer', dealer_multiplier), ('OEM/WD', oemwd_multiplier)]:
            if not (0 < value <= 1):
                raise ValueError(f"{name} multiplier must be between 0 and 1.")
    except ValueError as ve:
        messagebox.showerror("Multiplier Error", str(ve))
        status_label.config(text="Ready")
        process_button.config(state=tk.NORMAL)
        return

    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    if not file_path:
        process_button.config(state=tk.NORMAL)
        status_label.config(text="Ready")
        return

    threading.Thread(target=_process_file_worker, args=(file_path,), daemon=True).start()

# --- Save File Function ---
def save_file():
    if 'processed_data' not in globals():
        messagebox.showerror("Error", "No data to save!")
        return
    save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
    if save_path:
        try:
            processed_data.to_csv(save_path, index=False)
            messagebox.showinfo("Success", "File saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

# ---


# --- GUI Setup ---
root = tk.Tk()

# GUI Basics
root.title("Create Shopify Loadsheet")
root.geometry("700x700")

# Add label for downloading product list from site
label = tk.Label(root, text="Step 1: Download product list from Shopify if you haven't already (must be in CSV format)", font=("Helvetica", 10, "bold"))
label.pack(pady=10)

# Add label for apply multipliers (optional)
label = tk.Label(root, text="Step 2: Apply multipliers for additional pricing metrics (optional)", font=("Helvetica", 10, "bold"))
label.pack(pady=10)

# Add Multiplier Text Inputs
vcmd = root.register(validate_float_input)

jobber_label = tk.Label(root, text="Jobber Price Multiplier (default 0.85):") # Jobber multiplier
jobber_label.pack(pady=5)
jobber_price_entry = tk.Entry(root, validate="key", validatecommand=(vcmd, '%P'))
jobber_price_entry.pack(pady=5)
add_placeholder(jobber_price_entry, "0.85")

dealer_label = tk.Label(root, text="Dealer Price Multiplier (default 0.75):") # Dealer multiplier
dealer_label.pack(pady=5)
dealer_price_entry = tk.Entry(root, validate="key", validatecommand=(vcmd, '%P'))
dealer_price_entry.pack(pady=5)
add_placeholder(dealer_price_entry, "0.75")

oemwd_label = tk.Label(root, text="OEM/WD Price Multiplier (default 0.675):") # OEM/WD multiplier
oemwd_label.pack(pady=5)
oemwd_price_entry = tk.Entry(root, validate="key", validatecommand=(vcmd, '%P'))
oemwd_price_entry.pack(pady=5)
add_placeholder(oemwd_price_entry, "0.675")

# Checkbox: should we include jobber/dealer, oem/wd price in loadsheet?
jobber_price_var = tk.BooleanVar(value=True)
jobber_check = tk.Checkbutton(root, text="Include Jobber Price", variable=jobber_price_var)
jobber_check.pack(pady=5)

dealer_price_var = tk.BooleanVar(value=True)
dealer_check = tk.Checkbutton(root, text="Include Dealer Price", variable=dealer_price_var)
dealer_check.pack(pady=5)

oemwd_price_var = tk.BooleanVar(value=True)
oemwd_check = tk.Checkbutton(root, text="Include OEM/WD Price", variable=oemwd_price_var)
oemwd_check.pack(pady=5)

# Add label for processing CSV file
label = tk.Label(root, text="Step 3: Click button below to select and process your CSV file", font=("Helvetica", 10, "bold"))
label.pack(pady=10)

# Select CSV input download
process_button = tk.Button(root, text="Select CSV and Process", command=process_file)
process_button.pack(pady=10)

# Include metafields checkbox
include_product_metafields_var = tk.BooleanVar(value=True)
include_product_metafields_check = tk.Checkbutton(root, text="Include Product Metafields", variable=include_product_metafields_var)
include_product_metafields_check.pack(pady=5)

# Status label
status_label = tk.Label(root, text="", fg="blue")
status_label.pack(pady=10)

# Add label for saving processed file
label = tk.Label(root, text="Step 4: Click button below to save your newly processed file", font=("Helvetica", 10, "bold"))
label.pack(pady=10)

# Button to save newly processed file
save_button = tk.Button(root, text="Save Processed CSV", command=save_file, state=tk.DISABLED)
save_button.pack(pady=10)

root.mainloop()
