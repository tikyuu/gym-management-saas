import {
  Duration,
  RemovalPolicy,
  aws_cognito as cognito,
} from "aws-cdk-lib";
import { Construct } from "constructs";

interface CustomerAuthenticationConstructProps {
  customerOAuthCallbackUrls: string[];
  customerOAuthLogoutUrls: string[];
  customerUserPoolDomainPrefix: string;
  removalPolicy: RemovalPolicy;
  resourceNamePrefix: string;
  userPoolDeletionProtection: boolean;
}

export class CustomerAuthenticationConstruct extends Construct {
  public readonly appClient: cognito.IUserPoolClient;
  public readonly userPool: cognito.IUserPool;

  constructor(
    scope: Construct,
    id: string,
    props: CustomerAuthenticationConstructProps,
  ) {
    super(scope, id);

    this.userPool = new cognito.UserPool(this, "CustomerUserPool", {
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      autoVerify: {
        email: true,
      },
      deletionProtection: props.userPoolDeletionProtection,
      featurePlan: cognito.FeaturePlan.ESSENTIALS,
      mfa: cognito.Mfa.OPTIONAL,
      mfaSecondFactor: {
        otp: true,
        sms: false,
      },
      passwordPolicy: {
        minLength: 8,
        requireDigits: true,
        requireLowercase: true,
        requireSymbols: true,
        requireUppercase: true,
        tempPasswordValidity: Duration.days(7),
      },
      removalPolicy: props.removalPolicy,
      selfSignUpEnabled: true,
      signInAliases: {
        email: true,
      },
      signInCaseSensitive: false,
      userPoolName: `${props.resourceNamePrefix}-customer-user-pool`,
    });

    const userPoolDomain = this.userPool.addDomain("CustomerUserPoolDomain", {
      cognitoDomain: {
        domainPrefix: props.customerUserPoolDomainPrefix,
      },
      managedLoginVersion: cognito.ManagedLoginVersion.NEWER_MANAGED_LOGIN,
    });

    this.appClient = new cognito.UserPoolClient(this, "CustomerAppClient", {
      accessTokenValidity: Duration.minutes(60),
      enableTokenRevocation: true,
      generateSecret: false,
      idTokenValidity: Duration.minutes(60),
      oAuth: {
        callbackUrls: props.customerOAuthCallbackUrls,
        flows: {
          authorizationCodeGrant: true,
          implicitCodeGrant: false,
        },
        logoutUrls: props.customerOAuthLogoutUrls,
        scopes: [cognito.OAuthScope.OPENID, cognito.OAuthScope.EMAIL],
      },
      preventUserExistenceErrors: true,
      refreshTokenRotationGracePeriod: Duration.seconds(10),
      refreshTokenValidity: Duration.days(30),
      userPool: this.userPool,
      userPoolClientName: `${props.resourceNamePrefix}-customer-app-client`,
    });

    const managedLoginBranding = new cognito.CfnManagedLoginBranding(
      this,
      "CustomerManagedLoginBranding",
      {
        clientId: this.appClient.userPoolClientId,
        useCognitoProvidedValues: true,
        userPoolId: this.userPool.userPoolId,
      },
    );

    managedLoginBranding.node.addDependency(userPoolDomain);
  }
}
