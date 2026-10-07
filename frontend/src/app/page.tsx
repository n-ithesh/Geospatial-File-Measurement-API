import { UploadDropzone } from "../components/UploadDropzone";
import { FileList } from "../components/FileList";

export default function Home() {
  return (
    <div className="space-y-12">
      <section>
        <h2 className="text-xl font-semibold mb-4 text-gray-800">Upload a File</h2>
        <UploadDropzone />
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-4 text-gray-800">Recent Uploads</h2>
        <FileList />
      </section>
    </div>
  );
}
