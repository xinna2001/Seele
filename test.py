import os
import pandas as pd


def extract_query_columns(folder_path):
    all_query_columns = []
    # 遍历文件夹中的所有文件
    for filename in os.listdir(folder_path):
        if filename.endswith(('.xlsx', '.xls')):
            file_path = os.path.join(folder_path, filename)
            try:
                # 读取 Excel 文件的指定工作表
                df = pd.read_excel(file_path, sheet_name='Task_email_search')
                if 'Query' in df.columns:
                    # 提取 Query 列
                    query_column = df['Query']
                    all_query_columns.append(query_column)
            except Exception as e:
                print(f"读取文件 {filename} 时出错: {e}")
    if all_query_columns:
        # 合并所有 Query 列
        combined_df = pd.concat(all_query_columns, axis=0, ignore_index=True)
        output_path = os.path.join(folder_path, 'final.xlsx')
        # 将合并后的数据保存到新的 Excel 文件中
        combined_df.to_excel(output_path, index=False, header=['Query'])
        print(f"已将所有 Query 列合并到 {output_path}")
    else:
        print("未找到包含 Query 列的文件。")


if __name__ == "__main__":
    folder_path = r"C:\Users\zhangje1\Desktop\小语种多轮数据"
    extract_query_columns(folder_path)
    