import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  RiArrowLeftLine,
  RiArrowRightLine,
  RiSearchLine,
  RiMoreLine,
  RiEditLine,
  RiDeleteBinLine,
  RiDatabase2Line,
  RiArrowGoBackLine,
} from "@remixicon/react";
import {
  getModelInfo,
  listRecords,
  getRecord,
  updateRecord,
  deleteRecord,
  type ModelInfo,
  type PaginatedResponse,
} from "@/lib/admin-api";
import { toast } from "sonner";

type DialogMode = "edit" | "delete" | "view" | null;

export default function AdminModelBrowser() {
  const { modelName } = useParams<{ modelName: string }>();
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [records, setRecords] = useState<PaginatedResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [dialogMode, setDialogMode] = useState<DialogMode>(null);
  const [selectedRecord, setSelectedRecord] = useState<Record<string, unknown> | null>(null);
  const [formData, setFormData] = useState<Record<string, unknown>>({});
  const [submitting, setSubmitting] = useState(false);

  const fetchData = useCallback(async () => {
    if (!modelName) return;
    setLoading(true);
    try {
      const [info, data] = await Promise.all([
        getModelInfo(modelName),
        listRecords(modelName, { page, search, page_size: 20 }),
      ]);
      setModelInfo(info);
      setRecords(data);
    } catch {
      toast.error("Failed to load data");
    } finally {
      setLoading(false);
    }
  }, [modelName, page, search]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    const handler = setTimeout(() => {
      setPage(1);
    }, 300);
    return () => clearTimeout(handler);
  }, [search]);

  const openViewDialog = async (recordId: string) => {
    try {
      const record = await getRecord(modelName!, recordId);
      setSelectedRecord(record);
      setDialogMode("view");
    } catch {
      toast.error("Failed to load record");
    }
  };

  const openEditDialog = async (recordId: string) => {
    try {
      const record = await getRecord(modelName!, recordId);
      setSelectedRecord(record);
      setFormData({ ...record });
      setDialogMode("edit");
    } catch {
      toast.error("Failed to load record");
    }
  };

  const openDeleteDialog = (record: Record<string, unknown>) => {
    setSelectedRecord(record);
    setDialogMode("delete");
  };

  const closeDialog = () => {
    setDialogMode(null);
    setSelectedRecord(null);
    setFormData({});
  };

  const handleUpdate = async () => {
    if (!selectedRecord || !modelName) return;
    setSubmitting(true);
    try {
      // Only send editable fields
      const editableFields = getEditableFields();
      const updateData: Record<string, unknown> = {};
      for (const field of editableFields) {
        if (field in formData) {
          updateData[field] = formData[field];
        }
      }
      await updateRecord(modelName, String(selectedRecord.id), updateData);
      toast.success("Record updated successfully");
      closeDialog();
      fetchData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update record");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedRecord || !modelName) return;
    setSubmitting(true);
    try {
      await deleteRecord(modelName, String(selectedRecord.id));
      toast.success("Record deleted successfully");
      closeDialog();
      fetchData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete record");
    } finally {
      setSubmitting(false);
    }
  };

  // Get display columns (first 5 non-id columns + id)
  const getDisplayColumns = (): string[] => {
    if (!modelInfo) return [];
    const fields = modelInfo.fields.map((f) => f.name);
    const priority = ["id", "email", "full_name", "title", "name", "status", "role", "created_at"];
    const sorted = [...fields].sort((a, b) => {
      const aIdx = priority.indexOf(a);
      const bIdx = priority.indexOf(b);
      if (aIdx === -1 && bIdx === -1) return 0;
      if (aIdx === -1) return 1;
      if (bIdx === -1) return -1;
      return aIdx - bIdx;
    });
    return sorted.slice(0, 6);
  };

  // Get editable fields based on model config
  const getEditableFields = (): string[] => {
    if (!modelInfo) return [];
    // These are typically editable
    const nonEditable = ["id", "created_at", "updated_at", "password_hash"];
    return modelInfo.fields
      .filter((f) => !nonEditable.includes(f.name) && !f.primary_key)
      .map((f) => f.name);
  };

  const formatValue = (value: unknown): string => {
    if (value === null || value === undefined) return "-";
    if (typeof value === "boolean") return value ? "Yes" : "No";
    if (typeof value === "object") return JSON.stringify(value);
    if (typeof value === "string" && value.length > 50) return value.slice(0, 50) + "...";
    return String(value);
  };

  const renderFieldInput = (fieldName: string, fieldType: string) => {
    const value = formData[fieldName];
    const isJson = fieldType === "JSON";
    const isBoolean = fieldType === "Boolean";
    const isText = fieldType === "Text";

    if (isBoolean) {
      return (
        <select
          className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
          value={value === true ? "true" : "false"}
          onChange={(e) => setFormData({ ...formData, [fieldName]: e.target.value === "true" })}
        >
          <option value="true">Yes</option>
          <option value="false">No</option>
        </select>
      );
    }

    if (isJson || isText) {
      return (
        <Textarea
          value={isJson ? JSON.stringify(value, null, 2) : String(value ?? "")}
          onChange={(e) => {
            if (isJson) {
              try {
                setFormData({ ...formData, [fieldName]: JSON.parse(e.target.value) });
              } catch {
                // Keep as string if not valid JSON
              }
            } else {
              setFormData({ ...formData, [fieldName]: e.target.value });
            }
          }}
          rows={4}
        />
      );
    }

    return (
      <Input
        value={String(value ?? "")}
        onChange={(e) => setFormData({ ...formData, [fieldName]: e.target.value })}
      />
    );
  };

  const displayColumns = getDisplayColumns();
  const editableFields = getEditableFields();

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <Link to="/admin">
          <Button variant="ghost" size="icon">
            <RiArrowGoBackLine className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-xl font-semibold tracking-tight flex items-center gap-2">
            <RiDatabase2Line className="h-5 w-5" />
            {modelInfo?.display_name ?? modelName}
          </h1>
          <p className="text-sm text-muted-foreground">
            {modelInfo?.description} ({records?.total ?? 0} records)
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <RiSearchLine className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search records..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Field Info */}
      {modelInfo && (
        <Card>
          <CardHeader className="py-2 px-4">
            <CardTitle className="text-xs font-medium text-muted-foreground">
              Fields: {modelInfo.fields.map((f) => f.name).join(", ")}
            </CardTitle>
          </CardHeader>
        </Card>
      )}

      <Card>
        <CardContent className="p-0 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                {displayColumns.map((col) => (
                  <TableHead key={col} className="h-10 whitespace-nowrap">
                    {col}
                  </TableHead>
                ))}
                <TableHead className="h-10 text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                [...Array(5)].map((_, i) => (
                  <TableRow key={i}>
                    <TableCell colSpan={displayColumns.length + 1}>
                      <Skeleton className="h-10 w-full" />
                    </TableCell>
                  </TableRow>
                ))
              ) : records?.items.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={displayColumns.length + 1}
                    className="h-24 text-center"
                  >
                    <div className="flex flex-col items-center gap-2">
                      <RiDatabase2Line className="h-8 w-8 text-muted-foreground/50" />
                      <p className="text-sm text-muted-foreground">No records found</p>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                records?.items.map((record) => (
                  <TableRow key={String(record.id)}>
                    {displayColumns.map((col) => (
                      <TableCell
                        key={col}
                        className="py-2 text-sm max-w-[200px] truncate"
                      >
                        {col === "id" ? (
                          <button
                            onClick={() => openViewDialog(String(record.id))}
                            className="text-primary hover:underline font-mono text-xs"
                          >
                            {String(record[col]).slice(0, 8)}...
                          </button>
                        ) : (
                          formatValue(record[col])
                        )}
                      </TableCell>
                    ))}
                    <TableCell className="py-2 text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <RiMoreLine className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            onClick={() => openEditDialog(String(record.id))}
                          >
                            <RiEditLine className="h-4 w-4 mr-2" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="text-destructive"
                            onClick={() => openDeleteDialog(record)}
                          >
                            <RiDeleteBinLine className="h-4 w-4 mr-2" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Pagination */}
      {records && records.total_pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {records.page} of {records.total_pages}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              <RiArrowLeftLine className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= records.total_pages}
              onClick={() => setPage((p) => p + 1)}
            >
              <RiArrowRightLine className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* View Dialog */}
      <Dialog open={dialogMode === "view"} onOpenChange={closeDialog}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Record Details</DialogTitle>
            <DialogDescription>
              ID: {String(selectedRecord?.id ?? "")}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-2 py-4">
            {selectedRecord &&
              Object.entries(selectedRecord).map(([key, value]) => (
                <div
                  key={key}
                  className="grid grid-cols-3 gap-2 py-1 border-b border-border/50"
                >
                  <span className="text-sm font-medium text-muted-foreground">
                    {key}
                  </span>
                  <span className="col-span-2 text-sm break-all">
                    {typeof value === "object"
                      ? JSON.stringify(value, null, 2)
                      : String(value ?? "-")}
                  </span>
                </div>
              ))}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={closeDialog}>
              Close
            </Button>
            <Button onClick={() => openEditDialog(String(selectedRecord?.id))}>
              Edit
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={dialogMode === "edit"} onOpenChange={closeDialog}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Record</DialogTitle>
            <DialogDescription>
              Update the fields below. Only editable fields are shown.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            {editableFields.map((fieldName) => {
              const fieldInfo = modelInfo?.fields.find((f) => f.name === fieldName);
              if (!fieldInfo) return null;
              return (
                <div key={fieldName} className="grid gap-2">
                  <Label htmlFor={fieldName} className="flex items-center gap-2">
                    {fieldName}
                    <Badge variant="outline" className="text-xs font-normal">
                      {fieldInfo.type}
                    </Badge>
                  </Label>
                  {renderFieldInput(fieldName, fieldInfo.type)}
                </div>
              );
            })}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={closeDialog}>
              Cancel
            </Button>
            <Button onClick={handleUpdate} disabled={submitting}>
              {submitting ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={dialogMode === "delete"} onOpenChange={closeDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Record</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this record? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={closeDialog}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={submitting}>
              {submitting ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
