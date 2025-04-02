'use server';

import { auth, db } from "@/firebase/admin";
import { cookies } from "next/headers";

export async function signup(params:SignUpParams){
    const {uid, name, email} = params;
    try{

        const user = await db.collection("users").doc(uid).get();

        if(user.exists){
            return {
                success: false,
                message: "User already exists"
            }
        }

        await db.collection("users").doc(uid).set({
            name,
            email
        });

        return {
            success: true,
            message: "User created successfully"
        }

    }catch(e: any){
       console.log(e.message);
       if(e.code === "auth/email-already-in-use"){
           return {
            success: false,
            message: "Email already in use"
           };
       }    

    }
    return {
        success: false,
        message: "Something went wrong"
    }
}

export async function signIn(params: SignInParams){
    const {email, idToken} = params;

    try{
        const userCredential = await auth.getUserByEmail(email);

        if(!userCredential){
            return {
                success: false,
                message: "User does not exist"
            }
        }

        await setSessionCookie(idToken);

       
    }catch(e: any){
        console.log(e.message);
        return {
            success: false,
            message: "Failed to log into account. Please try again.",
          };
        
    }
}

export async function signInwithProvider(params: string){
    const  idToken = params;
    try{
        await setSessionCookie(idToken);
    }catch(e: any){
        console.log(e.message);
        return {
            success: false,
            message: "Failed to log into account. Please try again.",
          };
        
    }

}

export async function setSessionCookie(idToken: string){
    const cookieStore = await cookies();

    const sessionCoookie = await auth.createSessionCookie(idToken, {expiresIn: 60 * 60 * 24 * 5});

    cookieStore.set("session", sessionCoookie, {
        maxAge: 60 * 60 * 24 * 5,
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        path: "/",
        sameSite: "lax"
    });



}