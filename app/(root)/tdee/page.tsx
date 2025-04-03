import TDEECalculator from "@/components/TDEECalculator";
import { Card, CardContent } from "@/components/ui/card";

const TDEEPage = () => {
  return (
    <div className="flex justify-center items-center h-full">
      <Card className="w-full max-w-2xl">
        <CardContent className="p-8">
          <TDEECalculator />
        </CardContent>
      </Card>
    </div>
  );
};

export default TDEEPage;
