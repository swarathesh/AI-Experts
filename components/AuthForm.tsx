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
import {
  createUserWithEmailAndPassword,
  GoogleAuthProvider,
  signInWithEmailAndPassword,
  signInWithPopup,
} from "firebase/auth";

import { signIn, signup } from "@/lib/actions/auth.action";
import { auth } from "../firebase/client";

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
  async function onSubmit(values: z.infer<typeof formSchema>) {
    try {
      if (type === "sign-up") {
        const { name, email, password } = values;

        // Call the sign in function
        const userCredential = await createUserWithEmailAndPassword(
          auth,
          email,
          password
        );

        const result = await signup({
          uid: userCredential.user.uid,
          name: name!,
          email,
          password,
        });

        if (!result?.success) {
          toast.error(result.message);
          return;
        }

        toast.success("Signed up successfully");
        router.push("/sign-in");
        console.log(values);
      } else {
        const { email, password } = values;
        const userCredential = await signInWithEmailAndPassword(
          auth,
          email,
          password
        );
        const idToken = await userCredential.user.getIdToken();
        if (!idToken) {
          toast.error("An error occurred");
          return;
        }
        await signIn({ email, idToken });
        toast.success("signed in successfully");
        router.push("/");
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
        {/* Add Google Sign-Up Button */}
        <div className="mt-4 flex flex-col items-center">
          <p className="text-gray-200 self-center relative px-4">
            <span className="bg-card px-2">{`Or`}</span>
          </p>
          <button
            onClick={handleGoogleSignIn}
            className="google-signup-btn flex items-center justify-center bg-red-500 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded shadow mt-5"
          >
            <Image src="/google.png" alt="Google Icon" width={20} height={20} className="mr-2" />
            {isSingIn ? "Sign in with Google" : "Sign up with Google"}
          </button>
        </div>
      </div>
    </div>
  );

  async function handleGoogleSignIn() {
    try {
      const provider = new GoogleAuthProvider();
      const result = await signInWithPopup(auth, provider);
      const email = result.user.email;
      const idToken = await result.user.getIdToken();
      if (!email || !idToken) {
        toast.error("An error occurred during Google Sign-In");
        return;
      }
      await signIn({ email, idToken });
      toast.success("Signed in with Google successfully");
      router.push("/");
    } catch (error: any) {
      console.log(error);
      toast.error(`An error occurred ${error}`);
    }
  }
};

export default AuthForm;
