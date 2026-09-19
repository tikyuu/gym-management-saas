import { Stack, StackProps } from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import { Construct } from "constructs";

export class CiCdIdentityStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    const gitHubProvider = new iam.OpenIdConnectProvider(this, "GitHubOidcProvider", {
      url: "https://token.actions.githubusercontent.com",
      clientIds: ["sts.amazonaws.com"],
    });

    const gitHubDevDeployRole = new iam.Role(this, "GitHubDevDeployRole", {
      assumedBy: new iam.OpenIdConnectPrincipal(gitHubProvider, {
        StringEquals: {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub":
            "repo:tikyuu@224914317/gym-management-saas@1350988028:environment:development",
          "token.actions.githubusercontent.com:ref": "refs/heads/main",
        },
      }),
      roleName: "gym-management-dev-github-deploy-role",
    });

    gitHubDevDeployRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["sts:AssumeRole"],
        resources: [
          "arn:aws:iam::526811500752:role/cdk-hnb659fds-deploy-role-526811500752-ap-northeast-1",
          "arn:aws:iam::526811500752:role/cdk-hnb659fds-deploy-role-526811500752-us-east-1",
          "arn:aws:iam::526811500752:role/cdk-hnb659fds-file-publishing-role-526811500752-ap-northeast-1",
        ],
      }),
    );
  }
}
