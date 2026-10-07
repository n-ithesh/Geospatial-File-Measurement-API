"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="text-center py-12">
      <h2 className="text-3xl font-bold tracking-tight text-gray-900">Something went wrong!</h2>
      <p className="mt-4 text-gray-500">{error.message}</p>
      <button
        onClick={() => reset()}
        className="mt-6 inline-flex items-center rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500"
      >
        Try again
      </button>
    </div>
  );
}
