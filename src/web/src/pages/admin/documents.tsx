import { useMemo, useState } from "react";
import { RiFileUploadLine, RiSearchLine } from "@remixicon/react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  buildKnowledgeBaseCollectionName,
  KNOWLEDGE_BASE_CATEGORY_OPTIONS,
  KNOWLEDGE_BASE_EXAM_SECTION_OPTIONS,
  type KnowledgeBaseCategory,
  type KnowledgeBaseExamSection,
  searchAdminDocuments,
  uploadAdminDocument,
  type AdminDocumentSearchResult,
} from "@/lib/admin-api";

export default function AdminDocuments() {
  const [uploadCategory, setUploadCategory] = useState<KnowledgeBaseCategory>("exam");
  const [uploadExamSection, setUploadExamSection] =
    useState<KnowledgeBaseExamSection>("speaking");
  const [uploadCustomCollectionName, setUploadCustomCollectionName] = useState("");

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const [searchCategory, setSearchCategory] = useState<KnowledgeBaseCategory>("exam");
  const [searchExamSection, setSearchExamSection] =
    useState<KnowledgeBaseExamSection>("speaking");
  const [searchCustomCollectionName, setSearchCustomCollectionName] = useState("");

  const [searchQuery, setSearchQuery] = useState("");
  const [searchLimit, setSearchLimit] = useState(5);
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<AdminDocumentSearchResult[]>([]);

  const uploadCollectionName = useMemo(
    () =>
      buildKnowledgeBaseCollectionName({
        category: uploadCategory,
        examSection: uploadExamSection,
        customCollectionName: uploadCustomCollectionName,
      }),
    [uploadCategory, uploadExamSection, uploadCustomCollectionName]
  );

  const searchCollectionName = useMemo(
    () =>
      buildKnowledgeBaseCollectionName({
        category: searchCategory,
        examSection: searchExamSection,
        customCollectionName: searchCustomCollectionName,
      }),
    [searchCategory, searchExamSection, searchCustomCollectionName]
  );

  async function handleUpload() {
    if (!uploadCollectionName.trim()) {
      toast.error("Collection name is required");
      return;
    }
    if (!selectedFile) {
      toast.error("Please select a PDF file");
      return;
    }
    if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
      toast.error("Only PDF files are supported");
      return;
    }

    setUploading(true);
    try {
      const response = await uploadAdminDocument(
        {
          collectionName: uploadCollectionName,
          category: uploadCategory,
          examSection: uploadCategory === "exam" ? uploadExamSection : undefined,
          customCollectionName:
            uploadCategory === "custom" ? uploadCustomCollectionName : undefined,
        },
        selectedFile
      );
      toast.success(response.message || "PDF processing queued in background");
      setSelectedFile(null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function handleSearch() {
    if (!searchCollectionName.trim()) {
      toast.error("Collection name is required");
      return;
    }
    if (!searchQuery.trim()) {
      toast.error("Search query is required");
      return;
    }

    setSearching(true);
    try {
      const data = await searchAdminDocuments(
        {
          collectionName: searchCollectionName,
          category: searchCategory,
          examSection: searchCategory === "exam" ? searchExamSection : undefined,
          customCollectionName:
            searchCategory === "custom" ? searchCustomCollectionName : undefined,
        },
        searchQuery.trim(),
        searchLimit
      );
      setResults(data);
      if (data.length === 0) {
        toast.info("No matching chunks found");
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Search failed");
      setResults([]);
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Document Vector Store</h1>
        <p className="text-sm text-muted-foreground">
          Organize uploads by knowledge-base category so RAG search stays focused.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <RiFileUploadLine className="h-4 w-4" />
              Upload PDF
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="category-upload">Category</Label>
              <select
                id="category-upload"
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={uploadCategory}
                onChange={(e) => setUploadCategory(e.target.value as KnowledgeBaseCategory)}
              >
                {KNOWLEDGE_BASE_CATEGORY_OPTIONS.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>

            {uploadCategory === "exam" && (
              <div className="space-y-2">
                <Label htmlFor="exam-upload">Exam Section</Label>
                <select
                  id="exam-upload"
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={uploadExamSection}
                  onChange={(e) => setUploadExamSection(e.target.value as KnowledgeBaseExamSection)}
                >
                  {KNOWLEDGE_BASE_EXAM_SECTION_OPTIONS.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {uploadCategory === "custom" && (
              <div className="space-y-2">
                <Label htmlFor="custom-upload">Custom Collection Name</Label>
                <Input
                  id="custom-upload"
                  value={uploadCustomCollectionName}
                  onChange={(e) => setUploadCustomCollectionName(e.target.value)}
                  placeholder="e.g. teacher_notes_batch_a"
                />
              </div>
            )}

            <p className="rounded border bg-muted px-3 py-2 text-xs">
              Upload target collection: <strong>{uploadCollectionName}</strong>
            </p>

            <div className="space-y-2">
              <Label htmlFor="pdf-file">PDF File</Label>
              <Input
                id="pdf-file"
                type="file"
                accept="application/pdf"
                onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
              />
              <p className="text-xs text-muted-foreground">
                Processing happens in the background after upload.
              </p>
            </div>

            <Button onClick={handleUpload} disabled={uploading} className="w-full">
              {uploading ? "Queuing..." : "Upload and Queue Processing"}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <RiSearchLine className="h-4 w-4" />
              Search Category
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="category-search">Category</Label>
              <select
                id="category-search"
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={searchCategory}
                onChange={(e) => setSearchCategory(e.target.value as KnowledgeBaseCategory)}
              >
                {KNOWLEDGE_BASE_CATEGORY_OPTIONS.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>

            {searchCategory === "exam" && (
              <div className="space-y-2">
                <Label htmlFor="exam-search">Exam Section</Label>
                <select
                  id="exam-search"
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={searchExamSection}
                  onChange={(e) => setSearchExamSection(e.target.value as KnowledgeBaseExamSection)}
                >
                  {KNOWLEDGE_BASE_EXAM_SECTION_OPTIONS.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {searchCategory === "custom" && (
              <div className="space-y-2">
                <Label htmlFor="custom-search">Custom Collection Name</Label>
                <Input
                  id="custom-search"
                  value={searchCustomCollectionName}
                  onChange={(e) => setSearchCustomCollectionName(e.target.value)}
                  placeholder="e.g. teacher_notes_batch_a"
                />
              </div>
            )}

            <p className="rounded border bg-muted px-3 py-2 text-xs">
              Search target collection: <strong>{searchCollectionName}</strong>
            </p>

            <div className="space-y-2">
              <Label htmlFor="search-query">Query</Label>
              <Input
                id="search-query"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Ask something from uploaded docs"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="search-limit">Max Results</Label>
              <Input
                id="search-limit"
                type="number"
                min={1}
                max={20}
                value={searchLimit}
                onChange={(e) => {
                  const value = Number(e.target.value || 5);
                  setSearchLimit(Math.max(1, Math.min(20, value)));
                }}
              />
            </div>

            <Button onClick={handleSearch} disabled={searching} className="w-full">
              {searching ? "Searching..." : "Search Category"}
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Search Results</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {results.length === 0 ? (
            <p className="text-sm text-muted-foreground">No results yet.</p>
          ) : (
            results.map((item, idx) => (
              <div key={`${idx}-${item.content.slice(0, 20)}`} className="rounded-md border p-3 space-y-2">
                <Textarea value={item.content} readOnly className="min-h-24" />
                <pre className="overflow-x-auto rounded bg-muted p-2 text-xs">
                  {JSON.stringify(item.metadata ?? {}, null, 2)}
                </pre>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
