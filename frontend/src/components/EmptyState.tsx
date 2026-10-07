export function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-12">
      <h3 className="mt-2 text-sm font-semibold text-gray-900">{message}</h3>
    </div>
  );
}
