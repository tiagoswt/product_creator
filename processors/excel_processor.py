import os
import tempfile
import streamlit as st
import pandas as pd
import config


def is_csv_file(file):
    """
    Check if the uploaded file is a CSV file based on its name

    Args:
        file: An uploaded file object from Streamlit file uploader

    Returns:
        bool: True if file is CSV, False otherwise
    """
    if file is None:
        return False
    return file.name.lower().endswith(".csv")


def process_excel_file(file, header=0, nrows=None):
    """
    Process Excel or CSV file with custom header row

    Args:
        file: An Excel or CSV file object from Streamlit file uploader
        header (int): Row to use as the column names
        nrows (int): Number of rows to read (for preview)

    Returns:
        DataFrame: Processed pandas DataFrame
    """
    try:
        # Check if it's a CSV file
        if is_csv_file(file):
            # Read CSV file with robust parameters to handle various CSV formats
            df = pd.read_csv(
                file,
                header=header,
                nrows=nrows,
                sep=None,  # Let pandas auto-detect separator
                engine="python",  # Use python engine for better error handling
                encoding="utf-8",  # Default encoding
                on_bad_lines="skip",  # Skip bad lines instead of failing
                skipinitialspace=True,  # Skip spaces after delimiter
                quoting=1,  # Quote minimal - handles quotes properly
            )
        else:
            # Read Excel file with specified parameters
            df = pd.read_excel(file, header=header, nrows=nrows)

        # If header is not None, clean up the DataFrame
        if header is not None:
            # Convert object columns with mixed types to strings
            for col in df.select_dtypes(include=["object"]).columns:
                df[col] = df[col].astype(str)

            # Handle unnamed columns - either rename or drop them
            unnamed_cols = [col for col in df.columns if "Unnamed:" in str(col)]
            if unnamed_cols:
                # Option 1: Drop unnamed columns that are mostly empty
                for col in unnamed_cols:
                    if df[col].isna().mean() > 0.9:  # If more than 90% is empty
                        df = df.drop(columns=[col])
                    else:
                        # Option 2: Rename them
                        df = df.rename(
                            columns={col: f"Column_{str(col).split(':')[-1].strip()}"}
                        )

        return df
    except Exception as e:
        file_type = "CSV" if is_csv_file(file) else "Excel"

        # For CSV files, try alternative parsing methods
        if is_csv_file(file):
            st.warning(f"Initial CSV parsing failed: {str(e)}")
            st.info("Trying alternative CSV parsing methods...")

            # Try different separators and encodings
            for separator in [",", ";", "\t", "|"]:
                try:
                    file.seek(0)  # Reset file pointer
                    df = pd.read_csv(
                        file,
                        header=header,
                        nrows=nrows,
                        sep=separator,
                        engine="python",
                        encoding="utf-8",
                        on_bad_lines="skip",
                        skipinitialspace=True,
                        quoting=1,
                    )
                    st.success(f"Successfully parsed CSV with '{separator}' separator")
                    return df
                except:
                    continue

            # If all separators fail, try with different encoding
            try:
                file.seek(0)
                df = pd.read_csv(
                    file,
                    header=header,
                    nrows=nrows,
                    sep=None,
                    engine="python",
                    encoding="latin-1",  # Alternative encoding
                    on_bad_lines="skip",
                    skipinitialspace=True,
                )
                st.success("Successfully parsed CSV with latin-1 encoding")
                return df
            except:
                pass

        st.error(f"Error processing {file_type} file: {str(e)}")
        st.info(
            "Please check that your file is properly formatted. For CSV files, ensure consistent delimiters and proper encoding."
        )
        return None


def extract_excel_data(excel_file, excel_rows, header_row=0):
    """
    Extract text data from Excel or CSV file

    Args:
        excel_file: An Excel or CSV file object from Streamlit file uploader
        excel_rows (list): List of row indices to extract
        header_row (int): Row to use as the column names

    Returns:
        str: Consolidated text from Excel/CSV rows
    """
    if not excel_file or excel_rows is None:
        return None

    try:
        # Determine file extension for temporary file
        file_extension = ".csv" if is_csv_file(excel_file) else ".xlsx"

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=file_extension
        ) as tmp_file:
            tmp_file.write(excel_file.getvalue())
            tmp_path = tmp_file.name

        # Read file based on type
        if is_csv_file(excel_file):
            # Try robust CSV reading first
            try:
                df = pd.read_csv(
                    tmp_path,
                    header=header_row,
                    sep=None,
                    engine="python",
                    encoding="utf-8",
                    on_bad_lines="skip",
                    skipinitialspace=True,
                    quoting=1,
                )
            except:
                # Fallback to trying different separators
                df = None
                for separator in [",", ";", "\t", "|"]:
                    try:
                        df = pd.read_csv(
                            tmp_path,
                            header=header_row,
                            sep=separator,
                            engine="python",
                            encoding="utf-8",
                            on_bad_lines="skip",
                            skipinitialspace=True,
                            quoting=1,
                        )
                        break
                    except:
                        continue

                if df is None:
                    # Last resort - try with latin-1 encoding
                    df = pd.read_csv(
                        tmp_path,
                        header=header_row,
                        sep=None,
                        engine="python",
                        encoding="latin-1",
                        on_bad_lines="skip",
                        skipinitialspace=True,
                    )
        else:
            df = pd.read_excel(tmp_path, header=header_row)

        # Clean up DataFrame
        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].astype(str)

        for col in df.columns:
            if "Unnamed:" in str(col):
                df = df.rename(
                    columns={col: f"Column_{str(col).split(':')[-1].strip()}"}
                )

        # Filter by selected rows
        if excel_rows:
            df = df.iloc[excel_rows]

        # Convert dataframe to text
        file_type = "CSV" if is_csv_file(excel_file) else "EXCEL"
        excel_text = f"--- {file_type} DATA ---\n"
        for idx, row in df.iterrows():
            row_text = "\n".join([f"{col}: {value}" for col, value in row.items()])
            excel_text += f"ROW {idx}:\n{row_text}\n\n"

        os.unlink(tmp_path)  # Clean up the temp file

        return excel_text
    except Exception as e:
        if "tmp_path" in locals():
            os.unlink(tmp_path)  # Clean up the temp file even on error
        file_type = "CSV" if is_csv_file(excel_file) else "Excel"
        st.error(f"Error processing {file_type} data: {str(e)}")
        return None
