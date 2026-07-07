interface Props {
  text?: string;
  size?: "sm" | "md" | "lg";
}

const SIZES = { sm: "h-4 w-4", md: "h-8 w-8", lg: "h-12 w-12" };

export default function LoadingSpinner({ text, size = "md" }: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 p-8">
      <div
        className={`${SIZES[size]} animate-spin rounded-full border-2 border-gray-700 border-t-blue-500`}
      />
      {text && <p className="text-gray-400 text-sm">{text}</p>}
    </div>
  );
}
