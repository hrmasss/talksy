import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RiBookLine, RiAddLine } from "@remixicon/react";

export default function AdminExamsPage() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Exams</h1>
          <p className="text-sm text-muted-foreground">
            Create and manage exam templates
          </p>
        </div>
        <Button size="sm" className="gap-2">
          <RiAddLine className="h-4 w-4" />
          Create Exam
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="h-10">Name</TableHead>
                <TableHead className="h-10">Type</TableHead>
                <TableHead className="h-10">Questions</TableHead>
                <TableHead className="h-10">Duration</TableHead>
                <TableHead className="h-10 text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell colSpan={5} className="h-24 text-center">
                  <div className="flex flex-col items-center gap-2">
                    <RiBookLine className="h-8 w-8 text-muted-foreground/50" />
                    <p className="text-sm text-muted-foreground">
                      No exams created yet
                    </p>
                  </div>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
