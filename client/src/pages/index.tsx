import Head from 'next/head';
import FileUploadArea from "../components/FileUploadArea";
import FileQandAArea from "../components/FileQandAArea";

export default function FileQandA() {
  return (
    <div className="flex items-left text-left h-screen flex-col">
      <Head>
        <title>ChatGPT Retrieval Plugin</title>
      </Head>
      <div className="max-w-3xl mx-auto m-8 space-y-8 text-gray-800 dark:text-white">
        <h1 className="text-4xl">ChatGPT Retrieval Plugin</h1>

        <div className="">
          Upload your files here to add them to the database. You can
          also test queries here to reveal the relevant documents.
        </div>

        <FileUploadArea
          maxNumFiles={75}
          maxFileSizeMB={30}
        />
        <FileQandAArea />
      </div>
    </div>
  )
}
