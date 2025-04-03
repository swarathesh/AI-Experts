"use server";

import { auth, db } from "@/firebase/admin";
import { cookies } from "next/headers";

export async function signup(params: SignUpParams): Promise<unknown> {
  const { uid, name, email } = params;
  try {
    const user = await db.collection("users").doc(uid).get();

    if (user.exists) {
      return {
        success: false,
        message: "User already exists",
      };
    }

    await db.collection("users").doc(uid).set({
      name,
      email,
    });

    return {
      success: true,
      message: "User created successfully",
    };
  } catch (e: unknown) {
    console.log(e);
    return {
      success: false,
      message: "Something went wrong",
    };
  }
}

export async function signIn(params: SignInParams): Promise<unknown> {
  const { email, idToken } = params;

  try {
    const userCredential = await auth.getUserByEmail(email);

    if (!userCredential) {
      return {
        success: false,
        message: "User does not exist",
      };
    }

    await setSessionCookie(idToken);
  } catch (e: unknown) {
    console.log(e);
    return {
      success: false,
      message: "Failed to log into account. Please try again.",
    };
  }
}

export async function signInwithProvider(params: string): Promise<unknown> {
  const idToken = params;
  try {
    await setSessionCookie(idToken);
  } catch (e: unknown) {
    console.log(e);
    return {
      success: false,
      message: "Failed to log into account. Please try again.",
    };
  }
}

export async function setSessionCookie(idToken: string) {
  const cookieStore = await cookies();

  const sessionCoookie = await auth.createSessionCookie(idToken, {
    expiresIn: 60 * 60 * 24 * 5,
  });

  cookieStore.set("session", sessionCoookie, {
    maxAge: 60 * 60 * 24 * 5,
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    sameSite: "lax",
  });
}

export async function getCurrentUser(): Promise<User | null> {
  const cookieStore = await cookies();
  const sessionCookie = cookieStore.get("session")?.value;
  if (!sessionCookie) {
    return null;
  }
  try {
    const decodedClaims = await auth.verifySessionCookie(sessionCookie, true);

    const user = await db.collection("users").doc(decodedClaims.uid).get();

    if (!user.exists) {
      return null;
    }
    return {
        id: user.id,
        ...user.data()
 } as User;

  } catch (e: unknown) {
    console.log(e);
    return null;
  }
}

export async function isAuthenticatd() {
  const user = await getCurrentUser();
  return !!user;
}

// Sign out user by clearing the session cookie
export async function signOut() {
    const cookieStore = await cookies();
  
    cookieStore.delete("session");
  }
