export interface FileLite {
  expanded?: boolean;
  name: string;
  url?: string;
  type?: string;
  score?: number;
  size?: number;
  embedding?: number[]; // The file embedding -- or mean embedding if there are multiple embeddings for the file
  extractedText?: string; // The extracted text from the file
}