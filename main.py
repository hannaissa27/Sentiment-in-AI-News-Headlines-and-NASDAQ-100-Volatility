import backend
from backend.config import get_input_path, get_output_path

def main():
    # 1. Define where files are
    input_file = get_input_path("articles.xlsx")
    output_file = get_output_path("final_results.xlsx")

    # 2. Run the pipeline
    pipeline = backend.ResearchPipeline()
    pipeline.run(input_file, output_file)

if __name__ == "__main__":
    main()