import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
import chardet
import threading
import os

# --- Global variable to hold processed DataFrame ---
processed_df = None

def build_full_title(row):
    base_title = str(row.get('Title', '')).strip()
    options = []
    for opt_key in ['Option1 Value', 'Option2 Value', 'Option3 Value']:
        val = row.get(opt_key)
        if pd.notna(val):
            val_str = str(val).strip()
            if val_str and val_str.lower() != 'default title':
                options.append(val_str)
    return f"{base_title} - {' - '.join(options)}" if options else base_title

def get_image(images, idx):
    try:
        return images[idx]
    except (IndexError, TypeError):
        return '#N/A'

def _process_file_worker(file_path):
    global processed_df

    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            encoding = chardet.detect(raw_data)['encoding'] or 'utf-8'

        df = pd.read_csv(file_path, encoding=encoding, low_memory=False)

        df['Title'] = df['Title'].ffill().infer_objects(copy=False)
        df['Published'] = df['Published'].infer_objects().ffill().infer_objects(copy=False)
        df['Status'] = df['Status'].ffill().infer_objects(copy=False)

        if 'Fitment (product.metafields.convermax.fitment)' in df.columns and 'Handle' in df.columns:
            df['Fitment (product.metafields.convermax.fitment)'] = df.groupby('Handle')['Fitment (product.metafields.convermax.fitment)'].ffill().infer_objects(copy=False)
        if 'Type' in df.columns and 'Handle' in df.columns:
            df['Type'] = df.groupby('Handle')['Type'].ffill().infer_objects(copy=False)
        if 'Length (product.metafields.custom.length)' in df.columns and 'Handle' in df.columns:
            df['Length (product.metafields.custom.length)'] = df.groupby('Handle')['Length (product.metafields.custom.length)'].ffill().infer_objects(copy=False)
        if 'Width (product.metafields.custom.width)' in df.columns and 'Handle' in df.columns:
            df['Width (product.metafields.custom.width)'] = df.groupby('Handle')['Width (product.metafields.custom.width)'].ffill().infer_objects(copy=False)
        if 'Height (product.metafields.custom.height)' in df.columns and 'Handle' in df.columns:
            df['Height (product.metafields.custom.height)'] = df.groupby('Handle')['Height (product.metafields.custom.height)'].ffill().infer_objects(copy=False)

        df = df[
            (df['Variant Price'] > 0) &
            (df['Published'].astype(str).str.lower() == 'true') &
            (df['Status'].astype(str).str.lower() == 'active')
        ]

        df['Full Title'] = df.apply(build_full_title, axis=1)
        df['Variant Price'] = pd.to_numeric(df['Variant Price'], errors='coerce').map(lambda x: f"${x:,.2f}" if pd.notnull(x) else "")

        df['Weight (lb)'] = round(df['Variant Grams'] * 0.00220462, 2)

        if 'Fitment (product.metafields.convermax.fitment)' in df.columns:
            df['Fitment (product.metafields.convermax.fitment)'] = (
                df['Fitment (product.metafields.convermax.fitment)']
                .fillna('#N/A')
                .astype(str)
                .str.replace('|', ' ', regex=False)
                .str.replace('\n', ', ', regex=False)
            )

        for dim_col in ['Length (product.metafields.custom.length)', 'Width (product.metafields.custom.width)', 'Height (product.metafields.custom.height)']:
            if dim_col in df.columns:
                df[dim_col] = df[dim_col].fillna('#N/A').astype(str).str.replace("'", '', regex=False)

        df['Product Link'] = 'https://eddiemotorsports.com/products/' + df['Handle'].astype(str)

        if {'Handle', 'Variant SKU', 'Image Position', 'Image Src'}.issubset(df.columns):
            df['Image Position'] = pd.to_numeric(df['Image Position'], errors='coerce')
        image_df = df[['Handle', 'Variant SKU', 'Image Position', 'Image Src']].dropna(subset=['Image Src'])
        image_df = image_df.sort_values(['Handle', 'Variant SKU', 'Image Position'])
        image_groups = image_df.groupby(['Handle', 'Variant SKU'])['Image Src'].apply(list).to_dict()
        df['Image 2'] = df.apply(lambda row: get_image(image_groups.get((row['Handle'], row['Variant SKU'])), 1), axis=1)
        df['Image 3'] = df.apply(lambda row: get_image(image_groups.get((row['Handle'], row['Variant SKU'])), 2), axis=1)

        df.rename(columns={'Variant Image': 'Image 1'}, inplace=True)
        df['Image 1'] = df['Image 1'].fillna('#N/A').astype(str)
        df['Image 2'] = df['Image 2'].fillna('#N/A').astype(str)
        df['Image 3'] = df['Image 3'].fillna('#N/A').astype(str)

        final_variant_list = df.copy()
        final_column_list = [
            'Variant SKU', 'Full Title', 'Type', 'Handle', 'Title', 'Variant Price',
            'Length (product.metafields.custom.length)', 'Width (product.metafields.custom.width)', 'Height (product.metafields.custom.height)',
            'Weight (lb)', 'Fitment (product.metafields.convermax.fitment)', 'Body (HTML)',
            'Image 1', 'Image 2', 'Image 3', 'Product Link'
        ]

        for col in final_column_list:
            if col not in final_variant_list.columns:
                final_variant_list[col] = '#N/A'

        final_variant_list = final_variant_list[final_column_list]
        final_variant_list.rename(columns={
            'Variant SKU': 'Part #',
            'Type': 'Category',
            'Variant Price': 'Retail Price',
            'Length (product.metafields.custom.length)': 'Length (in)',
            'Width (product.metafields.custom.width)': 'Width (in)',
            'Height (product.metafields.custom.height)': 'Height (in)',
            'Fitment (product.metafields.convermax.fitment)': 'Fitment',
            'Body (HTML)': 'Description'
        }, inplace=True)
        final_variant_list.fillna("#N/A", inplace=True)

        processed_df = final_variant_list

        root.after(0, lambda: [
            status_label.config(text="Processing complete."),
            save_button.config(state=tk.NORMAL),
            process_button.config(state=tk.NORMAL),
            messagebox.showinfo("Success", "File processed. You can now save the output.")
        ])

    except Exception as e:
        import traceback
        traceback.print_exc()
        root.after(0, lambda: [
            status_label.config(text=f"Error: {e}"),
            process_button.config(state=tk.NORMAL),
            messagebox.showerror("Error", f"An error occurred:\n{e}")
        ])

def truncate_text(text, max_len=50):
    if len(text) <= max_len:
        return text
    else:
        return f"...{text[-(max_len - 3):]}"

def process_file():
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    if file_path:
        file_name = os.path.basename(file_path)
        display_name = truncate_text(file_name)

        # Set shortened filename label
        file_name_label.config(text=f"Selected File: {display_name}")

        # Bind hover events to show full filename on mouseover
        def on_enter(event):
            file_name_label.config(text=f"Selected File: {file_name}")

        def on_leave(event):
            file_name_label.config(text=f"Selected File: {display_name}")

        file_name_label.bind("<Enter>", on_enter)
        file_name_label.bind("<Leave>", on_leave)

        status_label.config(text="Processing...")
        save_button.config(state=tk.DISABLED)
        process_button.config(state=tk.DISABLED)
        threading.Thread(target=_process_file_worker, args=(file_path,), daemon=True).start()

def save_file():
    global processed_df
    if processed_df is None:
        messagebox.showwarning("No Data", "You must process a file before saving.")
        return

    output_file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
    if output_file_path:
        processed_df.to_csv(output_file_path, index=False)
        status_label.config(text="File saved successfully.")
        messagebox.showinfo("Saved", f"File saved to:\n{output_file_path}")
    else:
        status_label.config(text="Save cancelled.")

# --- GUI setup ---
root = tk.Tk()
root.title("EMS Loadsheet Builder")
root.geometry("400x170")  # Slightly taller for filename label

# --- Buttons ---
process_button = tk.Button(root, text="1. Select & Process CSV File", command=process_file)
process_button.pack(pady=(20, 5))

# --- Filename label ---
file_name_label = tk.Label(root, text="", fg="gray", anchor='w', justify='left')
file_name_label.pack()

save_button = tk.Button(root, text="2. Save Processed File", command=save_file, state=tk.DISABLED)
save_button.pack(pady=(10, 20))

# --- Status Label ---
status_label = tk.Label(root, text="", fg="blue")
status_label.pack(pady=5)

# --- Run GUI ---
root.mainloop()
