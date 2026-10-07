import Link from "next/link";

export default function NotFound() {
  return (
    <div className="text-center py-12">
      <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">404 - Not Found</h2>
      <p className="mt-4 text-lg text-gray-500">Could not find requested resource</p>
      <div className="mt-6">
        <Link href="/" className="text-base font-medium text-blue-600 hover:text-blue-500">
          Go back home <span aria-hidden="true">&rarr;</span>
        </Link>
      </div>
    </div>
  );
}
