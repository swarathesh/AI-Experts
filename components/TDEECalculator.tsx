"use client"

import { useState } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { Calculator } from "lucide-react"
import { Line, LineChart, Bar, BarChart, XAxis, YAxis, CartesianGrid, Legend, ReferenceLine } from "recharts"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ChartContainer, ChartTooltip } from "@/components/ui/chart"

const formSchema = z
  .object({
    gender: z.enum(["male", "female"]),
    age: z.coerce.number().min(15).max(100),
    weight: z.coerce.number().min(30).max(300),
    weightUnit: z.enum(["kg", "lbs"]),
    heightUnit: z.enum(["cm", "in", "ft"]),
    // Height fields - we'll validate based on the selected unit
    heightCm: z.coerce.number().min(100).max(250).optional(),
    heightIn: z.coerce.number().min(1).max(120).optional(),
    heightFt: z.coerce.number().min(1).max(8).optional(),
    heightFtIn: z.coerce.number().min(0).max(11).optional(),
    activityLevel: z.enum(["sedentary", "light", "moderate", "active", "very-active"]),
    targetWeight: z.coerce.number().min(30).max(300).optional(),
  })
  .refine(
    (data) => {
      // Validate height based on the selected unit
      if (data.heightUnit === "cm") {
        return data.heightCm !== undefined
      } else if (data.heightUnit === "in") {
        return data.heightIn !== undefined
      } else if (data.heightUnit === "ft") {
        return data.heightFt !== undefined
      }
      return false
    },
    {
      message: "Height is required",
      path: ["heightCm"],
    },
  )

type FormValues = z.infer<typeof formSchema>

const activityLevelMultipliers = {
  sedentary: 1.2, // Little or no exercise
  light: 1.375, // Light exercise 1-3 days/week
  moderate: 1.55, // Moderate exercise 3-5 days/week
  active: 1.725, // Hard exercise 6-7 days/week
  "very-active": 1.9, // Very hard exercise & physical job or 2x training
}

const activityLevelDescriptions = {
  sedentary: "Little or no exercise",
  light: "Light exercise 1-3 days/week",
  moderate: "Moderate exercise 3-5 days/week",
  active: "Hard exercise 6-7 days/week",
  "very-active": "Very hard exercise & physical job or 2x training",
}

export default function TDEECalculator() {
  const [result, setResult] = useState<{
    bmr: number
    tdee: number
    cutting: number
    maintenance: number
    bulking: number
    startingWeight: number
    weightUnit: string
    targetWeight: number | null
    targetIsHealthy: boolean
    weeksToTarget: {
      cutting: number | null
      bulking: number | null
    }
    projections: {
      cutting: { week: number; weight: number }[]
      maintenance: { week: number; weight: number }[]
      bulking: { week: number; weight: number }[]
      target?: { week: number; weight: number }[]
    }
  } | null>(null)

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      gender: "male",
      age: 30, // Initialize with default values instead of undefined
      weight: 70, // Initialize with default values instead of undefined
      weightUnit: "kg",
      heightUnit: "cm",
      heightCm: 170, // Initialize with default values instead of undefined
      heightIn: 67, // Initialize with default values instead of undefined
      heightFt: 5, // Initialize with default values instead of undefined
      heightFtIn: 7, // Initialize with default values
      activityLevel: "moderate",
      targetWeight: undefined, // Optional target weight
    },
  })

  // Watch the height unit to conditionally render the appropriate height input fields
  const heightUnit = form.watch("heightUnit")

  function calculateTDEE(data: FormValues) {
    // Convert weight to kg if needed
    const weightInKg = data.weightUnit === "lbs" ? data.weight * 0.453592 : data.weight

    // Convert height to cm based on the selected unit
    let heightInCm = 0
    if (data.heightUnit === "cm") {
      heightInCm = data.heightCm || 0
    } else if (data.heightUnit === "in") {
      heightInCm = (data.heightIn || 0) * 2.54
    } else if (data.heightUnit === "ft") {
      // Convert feet and inches to total inches, then to cm
      const totalInches = (data.heightFt || 0) * 12 + (data.heightFtIn || 0)
      heightInCm = totalInches * 2.54
    }

    // Calculate BMR using Mifflin-St Jeor Equation
    let bmr = 0
    if (data.gender === "male") {
      bmr = 10 * weightInKg + 6.25 * heightInCm - 5 * data.age + 5
    } else {
      bmr = 10 * weightInKg + 6.25 * heightInCm - 5 * data.age - 161
    }

    // Calculate TDEE
    const tdee = bmr * activityLevelMultipliers[data.activityLevel]

    return {
      bmr: Math.round(bmr),
      tdee: Math.round(tdee),
      cutting: Math.round(tdee * 0.8), // 20% deficit
      maintenance: Math.round(tdee),
      bulking: Math.round(tdee * 1.1), // 10% surplus
    }
  }

  function calculateHealthyWeight(heightInCm: number, gender: string, weightUnit: string): number {
    // Calculate healthy weight based on BMI of 22 (middle of healthy range 18.5-24.9)
    // Formula: BMI = weight(kg) / height(m)²
    const heightInMeters = heightInCm / 100
    let healthyWeightKg = 22 * (heightInMeters * heightInMeters)

    // Adjust slightly based on gender (men typically have more muscle mass)
    if (gender === "male") {
      healthyWeightKg *= 1.07
    } else {
      healthyWeightKg *= 0.95
    }

    // Convert to the user's preferred unit if needed
    if (weightUnit === "lbs") {
      return Math.round(healthyWeightKg * 2.20462)
    }

    return Math.round(healthyWeightKg)
  }

  function calculateWeightProjections(
    startingWeight: number,
    weightUnit: string,
    tdee: number,
    cutting: number,
    maintenance: number,
    bulking: number,
    targetWeight?: number,
  ) {
    // Convert weight to kg for calculations if needed
    const weightInKg = weightUnit === "lbs" ? startingWeight * 0.453592 : startingWeight
    const targetWeightInKg = targetWeight && weightUnit === "lbs" ? targetWeight * 0.453592 : targetWeight

    // Calculate weekly calorie difference
    const cuttingDeficitPerDay = tdee - cutting
    const bulkingSurplusPerDay = bulking - tdee

    // 7700 calories = approximately 1kg of body weight
    const cuttingWeeklyLoss = (cuttingDeficitPerDay * 7) / 7700
    const bulkingWeeklyGain = (bulkingSurplusPerDay * 7) / 7700

    // Default to 12 weeks, but extend if needed to show target achievement
    let weeks = 12

    // Extend projection if target weight is provided
    if (targetWeight) {
      // Calculate estimated weeks to target based on cutting/bulking rates
      const cuttingWeeksToTarget = Math.abs((weightInKg - targetWeightInKg!) / cuttingWeeklyLoss)
      const bulkingWeeksToTarget = Math.abs((targetWeightInKg! - weightInKg) / bulkingWeeklyGain)

      // Extend weeks if needed to reach target
      weeks = Math.max(weeks, cuttingWeeksToTarget, bulkingWeeksToTarget)
      weeks = Math.ceil(weeks) // Round up to nearest whole week
    }

    const cuttingProjection = []
    const maintenanceProjection = []
    const bulkingProjection = []
    const targetProjection = targetWeight ? [] : undefined

    for (let week = 0; week <= weeks; week++) {
      // Calculate projected weights
      const cuttingWeight = weightInKg - cuttingWeeklyLoss * week
      const maintenanceWeight = weightInKg
      const bulkingWeight = weightInKg + bulkingWeeklyGain * week

      // Convert back to original unit if needed
      const cuttingWeightConverted = weightUnit === "lbs" ? cuttingWeight / 0.453592 : cuttingWeight
      const maintenanceWeightConverted = weightUnit === "lbs" ? maintenanceWeight / 0.453592 : maintenanceWeight
      const bulkingWeightConverted = weightUnit === "lbs" ? bulkingWeight / 0.453592 : bulkingWeight

      cuttingProjection.push({
        week,
        weight: Number.parseFloat(cuttingWeightConverted.toFixed(1)),
      })

      maintenanceProjection.push({
        week,
        weight: Number.parseFloat(maintenanceWeightConverted.toFixed(1)),
      })

      bulkingProjection.push({
        week,
        weight: Number.parseFloat(bulkingWeightConverted.toFixed(1)),
      })

      // Add target weight line if provided
      if (targetWeight) {
        targetProjection?.push({
          week,
          weight: targetWeight,
        })
      }
    }

    return {
      cutting: cuttingProjection,
      maintenance: maintenanceProjection,
      bulking: bulkingProjection,
      target: targetProjection,
    }
  }

  function onSubmit(data: FormValues) {
    const tdeeResult = calculateTDEE(data)

    // Calculate height in cm for healthy weight calculation
    let heightInCm = 0
    if (data.heightUnit === "cm") {
      heightInCm = data.heightCm || 0
    } else if (data.heightUnit === "in") {
      heightInCm = (data.heightIn || 0) * 2.54
    } else if (data.heightUnit === "ft") {
      const totalInches = (data.heightFt || 0) * 12 + (data.heightFtIn || 0)
      heightInCm = totalInches * 2.54
    }

    // Use provided target weight or calculate a healthy weight
    const targetWeight = data.targetWeight || calculateHealthyWeight(heightInCm, data.gender, data.weightUnit)
    const targetIsHealthy = !data.targetWeight

    const projections = calculateWeightProjections(
      data.weight,
      data.weightUnit,
      tdeeResult.tdee,
      tdeeResult.cutting,
      tdeeResult.maintenance,
      tdeeResult.bulking,
      targetWeight,
    )

    // Calculate weeks to target
    const weeksToTarget = {
      cutting: null as number | null,
      bulking: null as number | null,
    }

    // If target weight is less than current weight, calculate weeks for cutting
    if (targetWeight < data.weight) {
      const weeklyLoss = Math.abs(projections.cutting[1].weight - projections.cutting[0].weight)
      if (weeklyLoss > 0) {
        weeksToTarget.cutting = Math.ceil(Math.abs(data.weight - targetWeight) / weeklyLoss)
      }
    }
    // If target weight is more than current weight, calculate weeks for bulking
    else if (targetWeight > data.weight) {
      const weeklyGain = Math.abs(projections.bulking[1].weight - projections.bulking[0].weight)
      if (weeklyGain > 0) {
        weeksToTarget.bulking = Math.ceil(Math.abs(targetWeight - data.weight) / weeklyGain)
      }
    }

    setResult({
      ...tdeeResult,
      startingWeight: data.weight,
      weightUnit: data.weightUnit,
      targetWeight,
      targetIsHealthy,
      weeksToTarget,
      projections,
    })
  }

  // Handle height unit change
  const handleHeightUnitChange = (value: string) => {
    form.setValue("heightUnit", value as "cm" | "in" | "ft")

    // Set appropriate default values when changing units instead of undefined
    if (value === "cm") {
      form.setValue("heightCm", 170)
    } else if (value === "in") {
      form.setValue("heightIn", 67)
    } else if (value === "ft") {
      form.setValue("heightFt", 5)
      form.setValue("heightFtIn", 7)
    }
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Calculator className="h-5 w-5" />
          <span>TDEE Calculator</span>
        </CardTitle>
        <CardDescription>
          Calculate your Total Daily Energy Expenditure based on your physical characteristics and activity level.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <FormField
              control={form.control}
              name="gender"
              render={({ field }) => (
                <FormItem className="space-y-3">
                  <FormLabel>Gender</FormLabel>
                  <FormControl>
                    <RadioGroup
                      onValueChange={field.onChange}
                      defaultValue={field.value}
                      className="flex flex-col space-y-1 sm:flex-row sm:space-x-4 sm:space-y-0"
                    >
                      <FormItem className="flex items-center space-x-3 space-y-0">
                        <FormControl>
                          <RadioGroupItem value="male" />
                        </FormControl>
                        <FormLabel className="font-normal">Male</FormLabel>
                      </FormItem>
                      <FormItem className="flex items-center space-x-3 space-y-0">
                        <FormControl>
                          <RadioGroupItem value="female" />
                        </FormControl>
                        <FormLabel className="font-normal">Female</FormLabel>
                      </FormItem>
                    </RadioGroup>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="age"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Age</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        placeholder="Enter your age"
                        {...field}
                        value={field.value || ""} // Ensure value is never undefined
                      />
                    </FormControl>
                    <FormDescription>Age in years (15-100)</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-3 gap-2">
                <FormField
                  control={form.control}
                  name="weight"
                  render={({ field }) => (
                    <FormItem className="col-span-2">
                      <FormLabel>Weight</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          placeholder="Enter your weight"
                          {...field}
                          value={field.value || ""} // Ensure value is never undefined
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="weightUnit"
                  render={({ field }) => (
                    <FormItem className="mt-auto">
                      <FormControl>
                        <div className="h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-center leading-6">
                          {field.value}
                        </div>
                      </FormControl>
                    </FormItem>
                  )}
                />
              </div>

              {/* Target Weight Input */}
              <div className="grid grid-cols-3 gap-2">
                <FormField
                  control={form.control}
                  name="targetWeight"
                  render={({ field }) => (
                    <FormItem className="col-span-2">
                      <FormLabel>Target Weight (optional)</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          placeholder="Enter target weight"
                          {...field}
                          value={field.value || ""} // Ensure value is never undefined
                        />
                      </FormControl>
                      <FormDescription>Leave blank to use healthy weight estimate</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              {/* Height Unit Selection */}
              <FormField
                control={form.control}
                name="heightUnit"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Height Unit</FormLabel>
                    <Select onValueChange={handleHeightUnitChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select height unit" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="cm">Centimeters (cm)</SelectItem>
                        <SelectItem value="in">Inches (in)</SelectItem>
                        <SelectItem value="ft">Feet & Inches (ft)</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Conditional Height Input based on selected unit */}
              {heightUnit === "cm" && (
                <FormField
                  control={form.control}
                  name="heightCm"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Height (cm)</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          placeholder="Enter height in cm"
                          {...field}
                          value={field.value || ""} // Ensure value is never undefined
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}

              {heightUnit === "in" && (
                <FormField
                  control={form.control}
                  name="heightIn"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Height (inches)</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          placeholder="Enter height in inches"
                          {...field}
                          value={field.value || ""} // Ensure value is never undefined
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}

              {heightUnit === "ft" && (
                <div className="grid grid-cols-2 gap-2">
                  <FormField
                    control={form.control}
                    name="heightFt"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Feet</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            placeholder="ft"
                            {...field}
                            value={field.value || ""} // Ensure value is never undefined
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="heightFtIn"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Inches</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            placeholder="in"
                            {...field}
                            value={field.value || 0} // Ensure value is never undefined
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              )}

              <FormField
                control={form.control}
                name="activityLevel"
                render={({ field }) => (
                  <FormItem className="sm:col-span-2">
                    <FormLabel>Activity Level</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select activity level" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="sedentary">Sedentary ({activityLevelDescriptions.sedentary})</SelectItem>
                        <SelectItem value="light">Light ({activityLevelDescriptions.light})</SelectItem>
                        <SelectItem value="moderate">Moderate ({activityLevelDescriptions.moderate})</SelectItem>
                        <SelectItem value="active">Active ({activityLevelDescriptions.active})</SelectItem>
                        <SelectItem value="very-active">
                          Very Active ({activityLevelDescriptions["very-active"]})
                        </SelectItem>
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      Choose the option that best describes your typical weekly activity
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <Button type="submit" className="w-full">
              Calculate TDEE
            </Button>
          </form>
        </Form>

        {result && (
          <>
            <div className="mt-8 space-y-4">
              <h3 className="text-xl font-semibold">Your Results</h3>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-lg border p-4">
                  <div className="text-sm font-medium text-muted-foreground">Basal Metabolic Rate (BMR)</div>
                  <div className="mt-1 text-2xl font-bold">{result.bmr} calories</div>
                  <div className="mt-1 text-xs text-muted-foreground">Calories your body needs at complete rest</div>
                </div>

                <div className="rounded-lg border bg-primary/5 p-4">
                  <div className="text-sm font-medium text-muted-foreground">Total Daily Energy Expenditure (TDEE)</div>
                  <div className="mt-1 text-2xl font-bold">{result.tdee} calories</div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    Your maintenance calories with activity level
                  </div>
                </div>
              </div>

              <Tabs defaultValue="maintenance" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="cutting">Cutting</TabsTrigger>
                  <TabsTrigger value="maintenance">Maintenance</TabsTrigger>
                  <TabsTrigger value="bulking">Bulking</TabsTrigger>
                </TabsList>
                <TabsContent value="cutting" className="rounded-lg border p-4">
                  <h4 className="font-medium">Weight Loss</h4>
                  <p className="text-2xl font-bold">{result.cutting} calories</p>
                  <p className="text-sm text-muted-foreground">20% calorie deficit for steady weight loss</p>
                </TabsContent>
                <TabsContent value="maintenance" className="rounded-lg border p-4">
                  <h4 className="font-medium">Maintenance</h4>
                  <p className="text-2xl font-bold">{result.maintenance} calories</p>
                  <p className="text-sm text-muted-foreground">Maintain your current weight</p>
                </TabsContent>
                <TabsContent value="bulking" className="rounded-lg border p-4">
                  <h4 className="font-medium">Weight Gain</h4>
                  <p className="text-2xl font-bold">{result.bulking} calories</p>
                  <p className="text-sm text-muted-foreground">10% calorie surplus for muscle gain</p>
                </TabsContent>
              </Tabs>

              {result.targetWeight && (
                <div className="mt-4 rounded-lg border p-4 bg-muted/10">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium text-muted-foreground">
                        {result.targetIsHealthy ? "Estimated Healthy Weight" : "Your Target Weight"}
                      </div>
                      <div className="mt-1 text-2xl font-bold">
                        {result.targetWeight} {result.weightUnit}
                      </div>
                    </div>

                    {(result.weeksToTarget.cutting || result.weeksToTarget.bulking) && (
                      <div className="text-right">
                        <div className="text-sm font-medium text-muted-foreground">Estimated Time to Reach Target</div>
                        <div className="mt-1 text-xl font-bold">
                          {result.weeksToTarget.cutting
                            ? `${result.weeksToTarget.cutting} weeks cutting`
                            : `${result.weeksToTarget.bulking} weeks bulking`}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {(result.weeksToTarget.cutting && result.weeksToTarget.cutting > 12) ||
                          (result.weeksToTarget.bulking && result.weeksToTarget.bulking > 12)
                            ? "Extends beyond 12-week projection"
                            : "Visible on the trajectory graph"}
                        </div>
                      </div>
                    )}
                  </div>

                  {result.targetIsHealthy && (
                    <p className="mt-2 text-xs text-muted-foreground">
                      This is an estimated healthy weight based on your height and gender using a BMI of approximately
                      22.
                    </p>
                  )}
                </div>
              )}
            </div>

            <div className="mt-10 space-y-8">
              <h4 className="text-lg font-medium">12-Week Weight Trajectory</h4>

              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  This graph shows your projected weight changes over 12 weeks if you follow each calorie plan
                  consistently.
                </p>

                <div className="h-[350px] w-full">
                  <ChartContainer
                    config={{
                      cutting: {
                        label: "Cutting (-20% calories)",
                        color: "hsl(var(--chart-1))",
                      },
                      maintenance: {
                        label: "Maintenance (balanced calories)",
                        color: "hsl(var(--chart-2))",
                      },
                      bulking: {
                        label: "Bulking (+10% calories)",
                        color: "hsl(var(--chart-3))",
                      },
                      target: {
                        label: result.targetIsHealthy ? "Healthy Weight Estimate" : "Target Weight",
                        color: "hsl(var(--chart-6))",
                      },
                    }}
                  >
                    <LineChart
                      data={Array.from({ length: 13 }, (_, i) => ({
                        week: i,
                        cutting: result.projections.cutting[i].weight,
                        maintenance: result.projections.maintenance[i].weight,
                        bulking: result.projections.bulking[i].weight,
                        target: result.projections.target ? result.projections.target[i].weight : null,
                      }))}
                      margin={{ top: 20, right: 30, left: 40, bottom: 20 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="week" label={{ value: "Weeks", position: "insideBottomRight", offset: -5 }} />
                      <YAxis
                        label={{
                          value: `Weight (${result.weightUnit})`,
                          angle: -90,
                          position: "insideLeft",
                          offset: -20,
                        }}
                      />
                      <Legend />
                      {/* Add reference line for target achievement time */}
                      {result.weeksToTarget.cutting && result.weeksToTarget.cutting <= 12 && (
                        <ReferenceLine
                          x={result.weeksToTarget.cutting}
                          stroke="var(--color-cutting)"
                          strokeDasharray="3 3"
                          label={{
                            value: `Target in ${result.weeksToTarget.cutting} weeks`,
                            position: "top",
                            fill: "var(--color-cutting)",
                            fontSize: 12,
                          }}
                        />
                      )}
                      {result.weeksToTarget.bulking && result.weeksToTarget.bulking <= 12 && (
                        <ReferenceLine
                          x={result.weeksToTarget.bulking}
                          stroke="var(--color-bulking)"
                          strokeDasharray="3 3"
                          label={{
                            value: `Target in ${result.weeksToTarget.bulking} weeks`,
                            position: "top",
                            fill: "var(--color-bulking)",
                            fontSize: 12,
                          }}
                        />
                      )}
                      <ChartTooltip
                        content={({ active, payload, label }) => {
                          if (active && payload && payload.length) {
                            return (
                              <div className="rounded-lg border bg-background p-2 shadow-md">
                                <p className="font-medium">Week {label}</p>
                                {payload.map((entry, index) => {
                                  if (entry.dataKey === "target" && entry.value === null) return null

                                  const planName =
                                    entry.dataKey === "cutting"
                                      ? "Cutting"
                                      : entry.dataKey === "maintenance"
                                        ? "Maintenance"
                                        : entry.dataKey === "bulking"
                                          ? "Bulking"
                                          : "Target Weight"

                                  if (entry.dataKey === "target") {
                                    return (
                                      <div key={`item-${index}`} className="flex items-center gap-2 py-1">
                                        <div
                                          className="h-3 w-3 rounded-full"
                                          style={{ backgroundColor: entry.color }}
                                        />
                                        <p className="text-sm">
                                          <span className="font-medium">{planName}:</span> {entry.value}{" "}
                                          {result.weightUnit}
                                          <span className="ml-1 text-xs text-muted-foreground">
                                            ({result.targetIsHealthy ? "Healthy weight estimate" : "Your goal"})
                                          </span>
                                        </p>
                                      </div>
                                    )
                                  }

                                  const diff = entry.value - result.startingWeight
                                  const sign = diff > 0 ? "+" : ""

                                  return (
                                    <div key={`item-${index}`} className="flex items-center gap-2 py-1">
                                      <div className="h-3 w-3 rounded-full" style={{ backgroundColor: entry.color }} />
                                      <p className="text-sm">
                                        <span className="font-medium">{planName}:</span> {entry.value}{" "}
                                        {result.weightUnit}
                                        <span className="ml-1 text-xs text-muted-foreground">
                                          ({sign}
                                          {diff.toFixed(1)} {result.weightUnit})
                                        </span>
                                      </p>
                                    </div>
                                  )
                                })}
                              </div>
                            )
                          }
                          return null
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="cutting"
                        stroke="var(--color-cutting)"
                        activeDot={{ r: 8 }}
                        strokeWidth={2}
                      />
                      <Line
                        type="monotone"
                        dataKey="maintenance"
                        stroke="var(--color-maintenance)"
                        activeDot={{ r: 8 }}
                        strokeWidth={2}
                      />
                      <Line
                        type="monotone"
                        dataKey="bulking"
                        stroke="var(--color-bulking)"
                        activeDot={{ r: 8 }}
                        strokeWidth={2}
                      />
                      {result.targetWeight && (
                        <Line
                          type="monotone"
                          dataKey="target"
                          stroke="var(--color-target, hsl(var(--chart-6)))"
                          strokeWidth={2}
                          strokeDasharray="5 5"
                        />
                      )}
                    </LineChart>
                  </ChartContainer>
                </div>
              </div>

              <div className="mt-10 space-y-8">
                <h3 className="text-xl font-semibold">Detailed Analysis</h3>

                <div className="space-y-4">
                  <h4 className="text-lg font-medium">Weekly Weight Difference</h4>
                  <p className="text-sm text-muted-foreground">
                    This chart shows the projected weight difference from your starting weight at the end of each 4-week
                    period.
                  </p>

                  <div className="h-[350px] w-full">
                    <ChartContainer
                      config={{
                        cutting: {
                          label: "Cutting (-20% calories)",
                          color: "hsl(var(--chart-1))",
                        },
                        maintenance: {
                          label: "Maintenance (balanced calories)",
                          color: "hsl(var(--chart-2))",
                        },
                        bulking: {
                          label: "Bulking (+10% calories)",
                          color: "hsl(var(--chart-3))",
                        },
                      }}
                    >
                      <BarChart
                        data={[
                          {
                            period: "4 Weeks",
                            cutting: Number.parseFloat(
                              (result.projections.cutting[4].weight - result.startingWeight).toFixed(1),
                            ),
                            maintenance: Number.parseFloat(
                              (result.projections.maintenance[4].weight - result.startingWeight).toFixed(1),
                            ),
                            bulking: Number.parseFloat(
                              (result.projections.bulking[4].weight - result.startingWeight).toFixed(1),
                            ),
                          },
                          {
                            period: "8 Weeks",
                            cutting: Number.parseFloat(
                              (result.projections.cutting[8].weight - result.startingWeight).toFixed(1),
                            ),
                            maintenance: Number.parseFloat(
                              (result.projections.maintenance[8].weight - result.startingWeight).toFixed(1),
                            ),
                            bulking: Number.parseFloat(
                              (result.projections.bulking[8].weight - result.startingWeight).toFixed(1),
                            ),
                          },
                          {
                            period: "12 Weeks",
                            cutting: Number.parseFloat(
                              (result.projections.cutting[12].weight - result.startingWeight).toFixed(1),
                            ),
                            maintenance: Number.parseFloat(
                              (result.projections.maintenance[12].weight - result.startingWeight).toFixed(1),
                            ),
                            bulking: Number.parseFloat(
                              (result.projections.bulking[12].weight - result.startingWeight).toFixed(1),
                            ),
                          },
                        ]}
                        margin={{ top: 20, right: 30, left: 40, bottom: 20 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="period" />
                        <YAxis
                          label={{
                            value: `Weight Change (${result.weightUnit})`,
                            angle: -90,
                            position: "insideLeft",
                            offset: -20,
                          }}
                        />
                        <Legend />
                        <ChartTooltip
                          content={({ active, payload, label }) => {
                            if (active && payload && payload.length) {
                              return (
                                <div className="rounded-lg border bg-background p-2 shadow-md">
                                  <p className="font-medium">{label}</p>
                                  {payload.map((entry, index) => {
                                    const planName =
                                      entry.dataKey === "cutting"
                                        ? "Cutting"
                                        : entry.dataKey === "maintenance"
                                          ? "Maintenance"
                                          : "Bulking"
                                    const sign = entry.value > 0 ? "+" : ""

                                    return (
                                      <div key={`item-${index}`} className="flex items-center gap-2 py-1">
                                        <div
                                          className="h-3 w-3 rounded-full"
                                          style={{ backgroundColor: entry.color }}
                                        />
                                        <p className="text-sm">
                                          <span className="font-medium">{planName}:</span> {sign}
                                          {entry.value} {result.weightUnit}
                                          <span className="ml-1 text-xs text-muted-foreground">
                                            from starting weight
                                          </span>
                                        </p>
                                      </div>
                                    )
                                  })}
                                </div>
                              )
                            }
                            return null
                          }}
                        />
                        <Bar dataKey="cutting" fill="var(--color-cutting)" radius={4} />
                        <Bar dataKey="maintenance" fill="var(--color-maintenance)" radius={4} />
                        <Bar dataKey="bulking" fill="var(--color-bulking)" radius={4} />
                      </BarChart>
                    </ChartContainer>
                  </div>
                </div>

                <div className="space-y-4">
                  <h4 className="text-lg font-medium">Weekly Rate of Change</h4>
                  <p className="text-sm text-muted-foreground">
                    This chart shows how much weight you would gain or lose each week on different diet plans.
                  </p>

                  <div className="h-[350px] w-full">
                    <ChartContainer
                      config={{
                        cutting: {
                          label: "Cutting (-20% calories)",
                          color: "hsl(var(--chart-1))",
                        },
                        maintenance: {
                          label: "Maintenance (balanced calories)",
                          color: "hsl(var(--chart-2))",
                        },
                        bulking: {
                          label: "Bulking (+10% calories)",
                          color: "hsl(var(--chart-3))",
                        },
                      }}
                    >
                      <BarChart
                        data={[
                          {
                            plan: "Cutting",
                            weeklyChange: Number.parseFloat(
                              (result.projections.cutting[1].weight - result.projections.cutting[0].weight).toFixed(2),
                            ),
                          },
                          {
                            plan: "Maintenance",
                            weeklyChange: Number.parseFloat(
                              (
                                result.projections.maintenance[1].weight - result.projections.maintenance[0].weight
                              ).toFixed(2),
                            ),
                          },
                          {
                            plan: "Bulking",
                            weeklyChange: Number.parseFloat(
                              (result.projections.bulking[1].weight - result.projections.bulking[0].weight).toFixed(2),
                            ),
                          },
                        ]}
                        margin={{ top: 20, right: 30, left: 40, bottom: 20 }}
                        layout="vertical"
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis
                          type="number"
                          label={{
                            value: `Weight Change per Week (${result.weightUnit})`,
                            position: "insideBottom",
                            offset: -5,
                          }}
                        />
                        <YAxis type="category" dataKey="plan" width={100} />
                        <Legend />
                        <ChartTooltip
                          content={({ active, payload, label }) => {
                            if (active && payload && payload.length) {
                              const value = payload[0].value
                              const sign = value > 0 ? "+" : ""
                              const caloriesPerDay =
                                label === "Cutting"
                                  ? result.cutting
                                  : label === "Maintenance"
                                    ? result.maintenance
                                    : result.bulking

                              return (
                                <div className="rounded-lg border bg-background p-2 shadow-md">
                                  <p className="font-medium">{label} Plan</p>
                                  <p className="text-sm">
                                    <span className="font-medium">Weekly change:</span> {sign}
                                    {value} {result.weightUnit}/week
                                  </p>
                                  <p className="text-sm">
                                    <span className="font-medium">Daily calories:</span> {caloriesPerDay} cal/day
                                  </p>
                                  <p className="mt-1 text-xs text-muted-foreground">
                                    {label === "Cutting"
                                      ? "20% calorie deficit"
                                      : label === "Maintenance"
                                        ? "Balanced calories"
                                        : "10% calorie surplus"}
                                  </p>
                                </div>
                              )
                            }
                            return null
                          }}
                        />
                        <Bar
                          dataKey="weeklyChange"
                          fill={(entry) =>
                            entry.plan === "Cutting"
                              ? "var(--color-cutting)"
                              : entry.plan === "Maintenance"
                                ? "var(--color-maintenance)"
                                : "var(--color-bulking)"
                          }
                          radius={4}
                        />
                      </BarChart>
                    </ChartContainer>
                  </div>
                </div>

                <div className="space-y-4">
                  <h4 className="text-lg font-medium">Body Composition Projection</h4>
                  <p className="text-sm text-muted-foreground">
                    This chart shows an estimated breakdown of fat vs. lean mass changes after 12 weeks on each plan.
                  </p>

                  <div className="h-[350px] w-full">
                    <ChartContainer
                      config={{
                        fatLoss: {
                          label: "Fat Loss/Gain",
                          color: "hsl(var(--chart-4))",
                        },
                        muscleLoss: {
                          label: "Muscle Loss/Gain",
                          color: "hsl(var(--chart-5))",
                        },
                      }}
                    >
                      <BarChart
                        data={[
                          {
                            plan: "Cutting",
                            fatLoss: Number.parseFloat(
                              (result.projections.cutting[12].weight - result.startingWeight) * 0.8,
                            ).toFixed(1),
                            muscleLoss: Number.parseFloat(
                              (result.projections.cutting[12].weight - result.startingWeight) * 0.2,
                            ).toFixed(1),
                          },
                          {
                            plan: "Maintenance",
                            fatLoss: 0,
                            muscleLoss: 0,
                          },
                          {
                            plan: "Bulking",
                            fatLoss: Number.parseFloat(
                              (result.projections.bulking[12].weight - result.startingWeight) * 0.3,
                            ).toFixed(1),
                            muscleLoss: Number.parseFloat(
                              (result.projections.bulking[12].weight - result.startingWeight) * 0.7,
                            ).toFixed(1),
                          },
                        ]}
                        margin={{ top: 20, right: 30, left: 40, bottom: 20 }}
                        layout="vertical"
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis
                          type="number"
                          label={{
                            value: `Weight Change (${result.weightUnit})`,
                            position: "insideBottom",
                            offset: -5,
                          }}
                        />
                        <YAxis type="category" dataKey="plan" width={100} />
                        <Legend />
                        <ChartTooltip
                          content={({ active, payload, label }) => {
                            if (active && payload && payload.length) {
                              const totalChange =
                                label === "Cutting"
                                  ? Number.parseFloat(
                                      (result.projections.cutting[12].weight - result.startingWeight).toFixed(1),
                                    )
                                  : label === "Maintenance"
                                    ? 0
                                    : Number.parseFloat(
                                        (result.projections.bulking[12].weight - result.startingWeight).toFixed(1),
                                      )

                              return (
                                <div className="rounded-lg border bg-background p-2 shadow-md">
                                  <p className="font-medium">{label} Plan (12 weeks)</p>
                                  <p className="text-sm">
                                    <span className="font-medium">Total change:</span> {totalChange > 0 ? "+" : ""}
                                    {totalChange} {result.weightUnit}
                                  </p>
                                  {payload.map((entry, index) => {
                                    const isPositive = Number.parseFloat(entry.value) > 0
                                    const label =
                                      entry.dataKey === "fatLoss"
                                        ? isPositive
                                          ? "Fat gain"
                                          : "Fat loss"
                                        : isPositive
                                          ? "Muscle gain"
                                          : "Muscle loss"

                                    return (
                                      <div key={`item-${index}`} className="flex items-center gap-2 py-1">
                                        <div
                                          className="h-3 w-3 rounded-full"
                                          style={{ backgroundColor: entry.color }}
                                        />
                                        <p className="text-sm">
                                          <span className="font-medium">{label}:</span> {Math.abs(entry.value)}{" "}
                                          {result.weightUnit}
                                        </p>
                                      </div>
                                    )
                                  })}
                                  <p className="mt-1 text-xs text-muted-foreground">
                                    Estimated breakdown based on typical body composition changes
                                  </p>
                                </div>
                              )
                            }
                            return null
                          }}
                        />
                        <Bar dataKey="fatLoss" fill="var(--color-fatLoss)" radius={4} stackId="a" />
                        <Bar dataKey="muscleLoss" fill="var(--color-muscleLoss)" radius={4} stackId="a" />
                      </BarChart>
                    </ChartContainer>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-8 space-y-2">
              <h4 className="text-lg font-medium">Disclaimer</h4>
              <p className="text-sm text-muted-foreground">
                This calculator uses the Mifflin-St Jeor Equation to estimate your TDEE and project weight changes.
                Results are estimates and may vary based on individual factors. Consult with a healthcare professional
                or registered dietitian for personalized advice.
              </p>
            </div>
          </>
        )}
      </CardContent>
      <CardFooter className="flex flex-col text-center text-sm text-muted-foreground">
        <p>
          This calculator uses the Mifflin-St Jeor Equation to estimate your TDEE. Results are estimates and may vary.
        </p>
      </CardFooter>
    </Card>
  )
}

