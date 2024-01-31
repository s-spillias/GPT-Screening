import os
import pandas as pd
import glob
from sklearn.metrics import confusion_matrix, cohen_kappa_score

# Function to extract confusion matrix elements
def extract_cm_elements(cm):
    tp, fn, fp, tn = cm.ravel()
    return tp, fp, fn, tn

# Load the main Excel file
main_df = pd.read_excel('CBFM/Human_Colab_Final.xlsx')
human_column = main_df['Human Accept']
colab_column = main_df['Colab-Accept']


# DataFrames to store results
results_human_column = pd.DataFrame(columns=['True Positive', 'False Positive', 'False Negative', 'True Negative', 'Kappa Statistic'])
results_colab_column = pd.DataFrame(columns=['True Positive', 'False Positive', 'False Negative', 'True Negative', 'Kappa Statistic'])

# Directory containing the 'Summary' Excel files
directory_path = 'CBFM/AI_Output'


# Iterate through each file in the directory
for file_path in glob.glob(os.path.join(directory_path, '**/*.xlsx'), recursive=True):
    xls = pd.ExcelFile(file_path)
    for sheet_name in xls.sheet_names:
        summary_df = pd.read_excel(file_path, sheet_name=sheet_name)
        print(file_path)
        # Assuming the relevant column in 'Summary' files is named 'Data'
        try:
            summary_col = summary_df['Summary Decision']
        except:
            continue
        if len(summary_col) < 1098:
            print("skipping")
            continue
        # Compute confusion matrices and Kappa statistics for human_column
        cm1 = confusion_matrix(human_column, summary_col, labels=["Yes", "No"])
        kappa1 = cohen_kappa_score(human_column, summary_col)
        tp1, fp1, fn1, tn1 = extract_cm_elements(cm1)
        results_human_column.loc[f"{file_path} - {sheet_name}"] = [tp1, fp1, fn1, tn1, kappa1]
        # Compute confusion matrices and Kappa statistics for colab_column
        cm2 = confusion_matrix(colab_column, summary_col, labels=["Yes", "No"])
        kappa2 = cohen_kappa_score(colab_column, summary_col)
        tp2, fp2, fn2, tn2 = extract_cm_elements(cm2)
        results_colab_column.loc[f"{file_path} - {sheet_name}"] = [tp2, fp2, fn2, tn2, kappa2]

# Compute confusion matrices and Kappa statistics for colab_column
cm3 = confusion_matrix(human_column, colab_column, labels=["Yes", "No"])
kappa3 = cohen_kappa_score(colab_column, human_column)
tp3, fp3, fn3, tn3 = extract_cm_elements(cm3)
results_colab_column.loc[f"Human"] = [tp3, fp3, fn3, tn3, kappa3]

# Display or save the results DataFrames
print("Results for human_column:")
print(results_human_column)
print("\nResults for colab_column:")
print(results_colab_column)

output_file = 'CBFM/Comparison_Results.xlsx'
with pd.ExcelWriter(output_file) as writer:
    results_human_column.to_excel(writer, sheet_name='Human-Compare')
    results_colab_column.to_excel(writer, sheet_name='Colab-Compare')

print(f"Results saved to {output_file}")