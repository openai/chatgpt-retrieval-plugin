import React, { memo, useCallback, useRef, useState } from "react";
import { Transition } from "@headlessui/react";
import axios from "axios";
import LoadingText from "./LoadingText";
import { SERVER_ADDRESS } from "../types/constants";
import { Answer } from "../types/answer";

function FileQandAArea() {
  const searchBarRef = useRef(null);
  const [answerError, setAnswerError] = useState("");
  const [searchResultsLoading, setSearchResultsLoading] =
    useState<boolean>(false);
  const [answer, setAnswer] = useState<Answer|null>(null);

  const handleSearch = useCallback(async () => {
    if (searchResultsLoading) {
      return;
    }

    const question = (searchBarRef?.current as any)?.value ?? "";
    setAnswer(null);

    if (!question) {
      setAnswerError("Please ask a question.");
      return;
    }

    setSearchResultsLoading(true);
    setAnswerError("");

    try {
      const answerResponse = await axios.post(
        `${SERVER_ADDRESS}/query`,
        {
          queries: [{
            "query": question
        }],
        },
        {
          headers: {
            "Authorization": "Bearer " + process.env.NEXT_PUBLIC_BEARER_TOKEN,
          }
        }
      );

      if (answerResponse.status === 200) {
        setAnswer(answerResponse.data.results[0]);
      } else {
        setAnswerError("Sorry, something went wrong!");
      }
    } catch (err: any) {
      setAnswerError("Sorry, something went wrong!");
    }

    setSearchResultsLoading(false);
  }, [searchResultsLoading]);

  const handleEnterInSearchBar = useCallback(
    async (event: React.SyntheticEvent) => {
      if ((event as any).key === "Enter") {
        await handleSearch();
      }
    },
    [handleSearch]
  );

  return (
    <div className="space-y-4 text-gray-800 dark:text-gray-50">
      <div className="mt-2">
        Submit a query to see the relevant docs:
      </div>
      <div className="space-y-2">
        <input
          className="border rounded border-gray-200 w-full py-1 px-2"
          placeholder="e.g. What were the key takeaways from the Q1 planning meeting?"
          name="search"
          ref={searchBarRef}
          onKeyDown={handleEnterInSearchBar}
        />
        <div
          className="rounded-md bg-gray-50 dark:bg-gray-800 py-1 px-4 w-max text-gray-500 dark:text-gray-300 hover:bg-gray-100 hover:dark:bg-gray-900 border border-gray-100 shadow cursor-pointer"
          onClick={handleSearch}
        >
          {searchResultsLoading ? (
            <LoadingText text="Answering question..." />
          ) : (
            "Ask question"
          )}
        </div>
      </div>
      <div>
        {answerError && <div className="text-red-500">{answerError}</div>}
        <Transition
          show={answer !== null}
          enter="transition duration-600 ease-out"
          enterFrom="transform opacity-0"
          enterTo="transform opacity-100"
          leave="transition duration-125 ease-out"
          leaveFrom="transform opacity-100"
          leaveTo="transform opacity-0"
          className="mb-8"
        >
          {answer && (
            <div className="space-y-2">
              {answer.results.map((result) => (
                <div key={result.id} className="mb-4">
                  <div>
                    <p>Score: {result.score}</p>
                    <p>Text: {result.text}</p>
                    <p>Metadata: {JSON.stringify(result.metadata)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Transition>
      </div>
    </div>
  );
}

export default memo(FileQandAArea);