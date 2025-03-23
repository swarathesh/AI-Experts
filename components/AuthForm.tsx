"use client";

import React from "react";
import Image from "next/image";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Form } from "@/components/ui/form";
import Link from "next/link";
import { toast } from "sonner";
import FormField from "./FormField";
import { useRouter } from "next/navigation";


const authFormSchema = (type: FormType) => {
  return z.object({
    name:
      type === "sign-up" ? z.string().min(2).max(50) : z.string().optional(),
    email: z.string().email(),
    password: z.string().min(6),
  });
};
const AuthForm = ({ type }: { type: FormType }) => {
  const isSingIn = type === "sign-in";

  const router = useRouter();

  const formSchema = authFormSchema(type);

  // 1. Define your form.
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      email: "",
      password: "",
    },
  });

  // 2. Define a submit handler.
  function onSubmit(values: z.infer<typeof formSchema>) {
    try {
      if (type === "sign-in") {
        // signIn(values)
        toast.success("Signed in successfully");
        router.push("/");
        console.log(values);
      } else {
        toast.success("Account created successfully");
        router.push("/sign-in");
        console.log(values);
      }
    } catch (error) {
      console.log(error);
      toast.error(`An error occurred ${error}`);
    }
  }

  return (
    <div className="card-border lg:min-w-[400px]">
      <div className="flex flex-col gap-6 card py-16 px-10">
        <div className="flex flex-row gap-2 justify-center">
          <Image src="/logo.svg" alt="logo" width={32} height={38} />
          <h2>AI Advisor</h2>
        </div>
        <h3>expert system for your everyday needs</h3>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
            {!isSingIn && (
              <FormField
                control={form.control}
                name="name"
                label="Name"
                placeholder="Enter your name"
              />
            )}
            <FormField
              control={form.control}
              name="email"
              label="Email"
              placeholder="Enter your email"
              type="email"
            />
            <FormField
              control={form.control}
              name="password"
              label="Password"
              placeholder="Enter your password"
              type="password"
            />
            <Button className="btn" type="submit">
              {isSingIn ? "Sign In" : "Create an account"}
            </Button>
          </form>
        </Form>
        <p className="text-center">
          {isSingIn ? "Don't have an account?" : "Already have an account?"}{" "}
          <Link
            className="text-blue-500"
            href={isSingIn ? "/sign-up" : "/sign-in"}
          >
            {isSingIn ? "Sign Up" : "Sign In"}
          </Link>
        </p>
      </div>
    </div>
  );
};

export default AuthForm;
